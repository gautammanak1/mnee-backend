import { Injectable, Logger, BadRequestException } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { ScheduledPost } from '../linkedin/schemas/scheduled-post.schema';
import {CronExpressionParser as cronParser} from 'cron-parser';
import { AIService } from '../ai/ai.service';
import { User } from '../user/schemas/user.schema';
import axios from 'axios';

@Injectable()
export class SchedulerService {
  private readonly logger = new Logger(SchedulerService.name);

  constructor(
    @InjectModel(ScheduledPost.name) private scheduledPostModel: Model<ScheduledPost>,
    @InjectModel(User.name) private userModel: Model<User>,
    private aiService: AIService,
  ) {}

  /**
   * Runs every minute to check and execute scheduled posts
   */
  @Cron(CronExpression.EVERY_MINUTE)
  async handleScheduledPosts() {
    this.logger.log('⏰ Checking for scheduled posts...');

    try {
      const now = new Date(); // UTC in Vercel
      const activeSchedules = await this.scheduledPostModel.find({ isActive: true });

      for (const schedule of activeSchedules) {
        try {
          // Initialize nextPostAt if missing
          if (!schedule.nextPostAt) {
            const interval = cronParser.parse(schedule.schedule);
            schedule.nextPostAt = interval.next().toDate();
            await schedule.save();
          }

          // Compare UTC times directly
          const shouldExecute = schedule.nextPostAt.getTime() <= now.getTime();

          this.logger.debug(
            `Schedule ${schedule._id}: Next UTC: ${schedule.nextPostAt.toISOString()} | Now: ${now.toISOString()} | Execute: ${shouldExecute}`,
          );

          if (!shouldExecute) continue;

          this.logger.log(`🚀 Executing scheduled post for user ${schedule.userId}, topic: ${schedule.topic}`);

          // Fetch user and LinkedIn credentials
          const user = await this.userModel.findById(schedule.userId);
          if (!user || !user.connectedAccounts?.linkedin?.accessToken) {
            this.logger.warn(`⚠ User ${schedule.userId} not found or LinkedIn not connected`);
            continue;
          }

          // Generate post content via AI
          const postContent = await this.aiService.generateLinkedInPostWithImage(
            schedule.topic,
            schedule.includeImage,
          );

          const fullText =
            postContent.hashtags.length > 0
              ? `${postContent.text}\n\n${postContent.hashtags.join(' ')}`
              : postContent.text;

          const token = user.connectedAccounts.linkedin.accessToken;
          const profile = user.connectedAccounts.linkedin.profile;
          const authorUrn = `urn:li:person:${profile.sub}`;

          // Post to LinkedIn
          if (schedule.includeImage && postContent.imageBuffer) {
            await this.postToLinkedInWithImage(token, authorUrn, fullText, postContent.imageBuffer, profile.sub);
          } else {
            await this.postToLinkedIn(token, authorUrn, fullText);
          }

          // Compute next execution
          const nextInterval = cronParser.parse(schedule.schedule);
          schedule.lastPostedAt = now;
          schedule.nextPostAt = nextInterval.next().toDate();
          schedule.postCount += 1;
          await schedule.save();

          const nextIST = new Date(schedule.nextPostAt.getTime() + 5.5 * 60 * 60 * 1000);
          this.logger.log(
            `✅ Next post: ${schedule.nextPostAt.toISOString()} (UTC) / ${nextIST.toLocaleString('en-IN')} (IST)`,
          );
        } catch (error) {
          this.logger.error(`❌ Error executing schedule ${schedule._id}: ${error.message}`);
        }
      }
    } catch (error) {
      this.logger.error(`🔥 Error in handleScheduledPosts: ${error.message}`);
    }
  }

  /**
   * Create a new scheduled post (frontend endpoint)
   */
  async createScheduledPost(
    userId: string,
    data: { topic: string; schedule: string; includeImage?: boolean; customText?: string },
  ): Promise<ScheduledPost> {
    try {
      // Parse cron safely without tz (works on Vercel)
      const interval = cronParser.parse(data.schedule);
      const nextUTC = interval.next().toDate();

      // Convert UTC → IST for logging (5.5h offset)
      const nextIST = new Date(nextUTC.getTime() + 5.5 * 60 * 60 * 1000);

      this.logger.log(
        `📅 Schedule "${data.schedule}" → Next UTC: ${nextUTC.toISOString()} | IST: ${nextIST.toLocaleString('en-IN')}`,
      );

      const scheduledPost = new this.scheduledPostModel({
        userId,
        topic: data.topic,
        customText: data.customText,
        schedule: data.schedule,
        includeImage: data.includeImage || false,
        isActive: true,
        nextPostAt: nextUTC, // store UTC-safe
        postCount: 0,
      });

      return await scheduledPost.save();
    } catch (error) {
      this.logger.error(`Invalid cron expression: ${data.schedule} | ${error.message}`);
      throw new BadRequestException(`Invalid cron expression: ${data.schedule}`);
    }
  }

  async getScheduledPosts(userId: string): Promise<ScheduledPost[]> {
    return this.scheduledPostModel.find({ userId }).sort({ createdAt: -1 });
  }

  async activateSchedule(userId: string, scheduleId: string): Promise<ScheduledPost> {
    const schedule = await this.scheduledPostModel.findOne({ _id: scheduleId, userId });
    if (!schedule) throw new BadRequestException('Schedule not found');

    schedule.isActive = true;
    if (!schedule.nextPostAt) {
      const interval = cronParser.parse(schedule.schedule);
      schedule.nextPostAt = interval.next().toDate();
    }
    return await schedule.save();
  }

  async deactivateSchedule(userId: string, scheduleId: string): Promise<ScheduledPost> {
    const schedule = await this.scheduledPostModel.findOne({ _id: scheduleId, userId });
    if (!schedule) throw new BadRequestException('Schedule not found');

    schedule.isActive = false;
    return await schedule.save();
  }

  async deleteSchedule(userId: string, scheduleId: string): Promise<void> {
    const result = await this.scheduledPostModel.deleteOne({ _id: scheduleId, userId });
    if (result.deletedCount === 0) throw new BadRequestException('Schedule not found');
  }

  /**
   * Post text-only to LinkedIn
   */
  private async postToLinkedIn(token: string, authorUrn: string, text: string): Promise<void> {
    await axios.post(
      'https://api.linkedin.com/v2/ugcPosts',
      {
        author: authorUrn,
        lifecycleState: 'PUBLISHED',
        specificContent: {
          'com.linkedin.ugc.ShareContent': {
            shareCommentary: { text },
            shareMediaCategory: 'NONE',
          },
        },
        visibility: { 'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC' },
      },
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-Restli-Protocol-Version': '2.0.0',
        },
      },
    );
  }

  /**
   * Post to LinkedIn with image upload
   */
  private async postToLinkedInWithImage(
    token: string,
    authorUrn: string,
    text: string,
    imageBuffer: Buffer,
    userId: string,
  ): Promise<void> {
    const registerResponse = await axios.post(
      'https://api.linkedin.com/v2/assets?action=registerUpload',
      {
        registerUploadRequest: {
          recipes: ['urn:li:digitalmediaRecipe:feedshare-image'],
          owner: `urn:li:person:${userId}`,
          serviceRelationships: [
            { relationshipType: 'OWNER', identifier: 'urn:li:userGeneratedContent' },
          ],
        },
      },
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-Restli-Protocol-Version': '2.0.0',
        },
      },
    );

    const uploadUrl =
      registerResponse.data.value.uploadMechanism['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']
        .uploadUrl;
    const asset = registerResponse.data.value.asset;

    // Upload image binary
    await axios.put(uploadUrl, imageBuffer, { headers: { 'Content-Type': 'image/jpeg' } });

    // Post with image
    await axios.post(
      'https://api.linkedin.com/v2/ugcPosts',
      {
        author: authorUrn,
        lifecycleState: 'PUBLISHED',
        specificContent: {
          'com.linkedin.ugc.ShareContent': {
            shareCommentary: { text },
            shareMediaCategory: 'IMAGE',
            media: [{ status: 'READY', media: asset, title: { text: 'LinkedIn Post Image' } }],
          },
        },
        visibility: { 'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC' },
      },
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-Restli-Protocol-Version': '2.0.0',
        },
      },
    );
  }
}
