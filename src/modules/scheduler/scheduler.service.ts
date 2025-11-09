import { Injectable, Logger, BadRequestException } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { ScheduledPost } from '../linkedin/schemas/scheduled-post.schema';
import { CronExpressionParser as cronParser } from 'cron-parser';
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
   * Runs every minute — checks and executes due scheduled posts
   */
  @Cron(CronExpression.EVERY_MINUTE)
  async handleScheduledPosts() {
    this.logger.log('⏰ Checking for scheduled posts...');

    try {
      const nowUTC = new Date(); // UTC time (Vercel uses UTC)
      const activeSchedules = await this.scheduledPostModel.find({ isActive: true });

      for (const schedule of activeSchedules) {
        try {
          // Initialize nextPostAt if missing
          if (!schedule.nextPostAt) {
            schedule.nextPostAt = this.getNextUTC(schedule.schedule);
            await schedule.save();
          }

          const shouldExecute = schedule.nextPostAt.getTime() <= nowUTC.getTime();

          if (!shouldExecute) continue;

          this.logger.log(
            `🚀 Running scheduled post for ${schedule.userId} | Topic: ${schedule.topic}`,
          );

          const user = await this.userModel.findById(schedule.userId);
          if (!user || !user.connectedAccounts?.linkedin?.accessToken) {
            this.logger.warn(`⚠️ User ${schedule.userId} not connected to LinkedIn`);
            continue;
          }

          // Generate content
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

          if (schedule.includeImage && postContent.imageBuffer) {
            await this.postToLinkedInWithImage(token, authorUrn, fullText, postContent.imageBuffer, profile.sub);
          } else {
            await this.postToLinkedIn(token, authorUrn, fullText);
          }

          // Update next run
          schedule.lastPostedAt = nowUTC;
          schedule.nextPostAt = this.getNextUTC(schedule.schedule);
          schedule.postCount += 1;
          await schedule.save();

          const nextIST = this.toIST(schedule.nextPostAt);
          this.logger.log(
            `✅ Next post scheduled for ${schedule.nextPostAt.toISOString()} (UTC) / ${nextIST} (IST)`,
          );
        } catch (error) {
          this.logger.error(`❌ Error executing schedule ${schedule._id}: ${error.message}`);
        }
      }
    } catch (error) {
      this.logger.error(`🔥 Scheduler handler error: ${error.message}`);
    }
  }

  /**
   * Create a new schedule (user creates from dashboard)
   */
  async createScheduledPost(
    userId: string,
    data: { topic: string; schedule: string; includeImage?: boolean; customText?: string },
  ): Promise<ScheduledPost> {
    try {
      const nextUTC = this.getNextUTC(data.schedule);
      const nextIST = this.toIST(nextUTC);

      this.logger.log(
        `📅 Schedule "${data.schedule}" parsed → Next UTC: ${nextUTC.toISOString()} | IST: ${nextIST}`,
      );

      const scheduledPost = new this.scheduledPostModel({
        userId,
        topic: data.topic,
        customText: data.customText,
        schedule: data.schedule,
        includeImage: data.includeImage || false,
        isActive: true,
        nextPostAt: nextUTC,
        postCount: 0,
      });

      return await scheduledPost.save();
    } catch (err) {
      this.logger.error(`Invalid cron "${data.schedule}": ${err.message}`);
      throw new BadRequestException(`Invalid cron expression: ${data.schedule}`);
    }
  }

  /** Helper: Safely parse cron and return next UTC Date */
  private getNextUTC(cron: string): Date {
    try {
      const options = { tz: 'UTC' }; // Explicitly use UTC for consistency
      const interval = cronParser.parse(cron, options);
      const next = interval.next().toDate();
      if (isNaN(next.getTime())) throw new Error('Invalid next run date');
      return next;
    } catch (err) {
      throw new Error(`Invalid cron or unsupported format: ${cron}`);
    }
  }

  /** Helper: Convert UTC Date → IST formatted string */
  private toIST(date: Date): string {
    const ist = new Date(date.getTime() + 5.5 * 60 * 60 * 1000);
    return ist.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
  }

  async getScheduledPosts(userId: string): Promise<ScheduledPost[]> {
    return this.scheduledPostModel.find({ userId }).sort({ createdAt: -1 });
  }

  async activateSchedule(userId: string, scheduleId: string): Promise<ScheduledPost> {
    const schedule = await this.scheduledPostModel.findOne({ _id: scheduleId, userId });
    if (!schedule) throw new BadRequestException('Schedule not found');

    schedule.isActive = true;
    schedule.nextPostAt = this.getNextUTC(schedule.schedule);
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

  /** LinkedIn posting helpers */
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
          serviceRelationships: [{ relationshipType: 'OWNER', identifier: 'urn:li:userGeneratedContent' }],
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

    await axios.put(uploadUrl, imageBuffer, { headers: { 'Content-Type': 'image/jpeg' } });

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