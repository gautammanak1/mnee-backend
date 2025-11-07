import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { ScheduledPost } from '../linkedin/schemas/scheduled-post.schema';
import {CronExpressionParser} from 'cron-parser';
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
   * Check and execute scheduled posts every minute
   */
  @Cron(CronExpression.EVERY_MINUTE)
  async handleScheduledPosts() {
    this.logger.log('Checking for scheduled posts...');

    try {
      const now = new Date();
      const activeSchedules = await this.scheduledPostModel.find({
        isActive: true,
      });

      // Use IST (India Standard Time) timezone
      const timezone = process.env.TZ || 'Asia/Kolkata';

      for (const schedule of activeSchedules) {
        try {
          // If nextPostAt is not set, initialize it
          if (!schedule.nextPostAt) {
            const interval = CronExpressionParser.parse(schedule.schedule, {
              currentDate: now,
              tz: timezone,
            });
            schedule.nextPostAt = interval.next().toDate();
            await schedule.save();
          }

          // Check if it's time to execute (compare UTC times directly)
          const shouldExecute = schedule.nextPostAt.getTime() <= now.getTime();

          this.logger.debug(
            `Schedule ${schedule._id}: Next post at (UTC): ${schedule.nextPostAt.toISOString()}, Now (UTC): ${now.toISOString()}, Should execute: ${shouldExecute}`
          );

          if (shouldExecute) {
            this.logger.log(`Executing scheduled post for user ${schedule.userId}, topic: ${schedule.topic}`);

            try {
              // Get user and LinkedIn token
              const user = await this.userModel.findById(schedule.userId);
              if (!user || !user.connectedAccounts?.linkedin?.accessToken) {
                this.logger.warn(`User ${schedule.userId} not found or LinkedIn not connected`);
                continue;
              }

              // Generate post content
              const postContent = await this.aiService.generateLinkedInPostWithImage(
                schedule.topic,
                schedule.includeImage,
              );

              // Combine text and hashtags
              const fullText = postContent.hashtags.length > 0
                ? `${postContent.text}\n\n${postContent.hashtags.join(' ')}`
                : postContent.text;

              // Post to LinkedIn
              const token = user.connectedAccounts.linkedin.accessToken;
              const profile = user.connectedAccounts.linkedin.profile;
              const authorUrn = `urn:li:person:${profile.sub}`;

              if (schedule.includeImage && postContent.imageBuffer) {
                // Post with image
                await this.postToLinkedInWithImage(token, authorUrn, fullText, postContent.imageBuffer, profile.sub);
              } else {
                // Post text only
                await this.postToLinkedIn(token, authorUrn, fullText);
              }

              // Update schedule
              const nextInterval = CronExpressionParser.parse(schedule.schedule, {
                currentDate: now,
                tz: timezone,
              });
              schedule.lastPostedAt = now;
              schedule.nextPostAt = nextInterval.next().toDate();
              schedule.postCount += 1;
              await schedule.save();
              
              this.logger.log(
                `Next post scheduled for: ${schedule.nextPostAt.toISOString()} (UTC) / ${schedule.nextPostAt.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} (IST)`
              );

              this.logger.log(`Successfully posted scheduled post for user ${schedule.userId}`);
            } catch (error) {
              this.logger.error(`Error posting scheduled content for user ${schedule.userId}: ${error.message}`);
            }
          }
        } catch (error) {
          this.logger.error(`Error executing schedule ${schedule._id}: ${error.message}`);
        }
      }
    } catch (error) {
      this.logger.error(`Error in scheduled posts handler: ${error.message}`);
    }
  }

  /**
   * Create a new scheduled post
   */
  async createScheduledPost(userId: string, data: {
    topic: string;
    schedule: string;
    includeImage?: boolean;
    customText?: string;
  }): Promise<ScheduledPost> {
    // Parse cron to get next execution time with IST timezone
    const timezone = process.env.TZ || 'Asia/Kolkata';
    
    // Parse cron expression with IST timezone
    const interval = CronExpressionParser.parse(data.schedule, {
      tz: timezone,
    });
    
    // Get next execution time (returns UTC Date object representing IST time)
    const nextPostAt = interval.next().toDate();
    
    // Log for verification
    this.logger.log(
      `Schedule "${data.schedule}" - Next post: ${nextPostAt.toISOString()} (UTC) = ${nextPostAt.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} (IST)`
    );

    const scheduledPost = new this.scheduledPostModel({
      userId,
      topic: data.topic,
      customText: data.customText,
      schedule: data.schedule,
      includeImage: data.includeImage || false,
      isActive: true,
      nextPostAt,
      postCount: 0,
    });

    return scheduledPost.save();
  }

  /**
   * Get all scheduled posts for a user
   */
  async getScheduledPosts(userId: string): Promise<ScheduledPost[]> {
    return this.scheduledPostModel.find({ userId }).sort({ createdAt: -1 });
  }

  /**
   * Activate a schedule
   */
  async activateSchedule(userId: string, scheduleId: string): Promise<ScheduledPost> {
    const schedule = await this.scheduledPostModel.findOne({
      _id: scheduleId,
      userId,
    });

    if (!schedule) {
      throw new Error('Schedule not found');
    }

    schedule.isActive = true;
    if (!schedule.nextPostAt) {
      const timezone = process.env.TZ || 'Asia/Kolkata';
      const interval = CronExpressionParser.parse(schedule.schedule, {
        tz: timezone,
      });
      schedule.nextPostAt = interval.next().toDate();
    }
    return schedule.save();
  }

  /**
   * Deactivate a schedule
   */
  async deactivateSchedule(userId: string, scheduleId: string): Promise<ScheduledPost> {
    const schedule = await this.scheduledPostModel.findOne({
      _id: scheduleId,
      userId,
    });

    if (!schedule) {
      throw new Error('Schedule not found');
    }

    schedule.isActive = false;
    return schedule.save();
  }

  /**
   * Delete a schedule
   */
  async deleteSchedule(userId: string, scheduleId: string): Promise<void> {
    const result = await this.scheduledPostModel.deleteOne({
      _id: scheduleId,
      userId,
    });

    if (result.deletedCount === 0) {
      throw new Error('Schedule not found');
    }
  }

  /**
   * Post text to LinkedIn
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
        visibility: {
          'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC',
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
  }

  /**
   * Post to LinkedIn with image
   */
  private async postToLinkedInWithImage(
    token: string,
    authorUrn: string,
    text: string,
    imageBuffer: Buffer,
    userId: string,
  ): Promise<void> {
    // Upload image
    const registerResponse = await axios.post(
      'https://api.linkedin.com/v2/assets?action=registerUpload',
      {
        registerUploadRequest: {
          recipes: ['urn:li:digitalmediaRecipe:feedshare-image'],
          owner: `urn:li:person:${userId}`,
          serviceRelationships: [
            {
              relationshipType: 'OWNER',
              identifier: 'urn:li:userGeneratedContent',
            },
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

    const uploadUrl = registerResponse.data.value.uploadMechanism['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest'].uploadUrl;
    const asset = registerResponse.data.value.asset;

    // Upload image
    await axios.put(uploadUrl, imageBuffer, {
      headers: {
        'Content-Type': 'image/jpeg',
      },
    });

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
            media: [
              {
                status: 'READY',
                media: asset,
                title: {
                  text: 'LinkedIn Post Image',
                },
              },
            ],
          },
        },
        visibility: {
          'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC',
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
  }
}