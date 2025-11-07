import { 
  Injectable, 
  UnauthorizedException, 
  InternalServerErrorException,
  NotFoundException,
  BadRequestException,
} from '@nestjs/common';
import axios from 'axios';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User } from '../user/schemas/user.schema';
import { ScheduledPost } from './schemas/scheduled-post.schema';
import { AIService } from '../ai/ai.service';
import { CreateScheduledPostDto } from './dto/create-scheduled-post.dto';

@Injectable()
export class LinkedInService {
  constructor(
    @InjectModel(User.name) private userModel: Model<User>,
    @InjectModel(ScheduledPost.name) private scheduledPostModel: Model<ScheduledPost>,
    private aiService: AIService,
  ) {}

  /**
   * Generate LinkedIn OAuth URL
   */
  generateAuthUrl(userId: string) {
    const clientId = process.env.LINKEDIN_CLIENT_ID;
    const redirectUri = process.env.LINKEDIN_REDIRECT_URI;
    const scope = process.env.LINKEDIN_SCOPE || '';
    const state = `linkedin-${userId}-${Date.now()}`;
    console.log(redirectUri)
    const authUrl = `https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=${clientId}&redirect_uri=${redirectUri}&state=${state}&scope=${encodeURIComponent(scope)}`;
    return { authUrl };
  }

  /**
   * Exchange authorization code for access token
   */
  async handleCallback(code: string, state: string) {
    try {
      const tokenResponse = await axios.post(
        'https://www.linkedin.com/oauth/v2/accessToken',
        new URLSearchParams({
          grant_type: 'authorization_code',
          code,
          redirect_uri: process.env.LINKEDIN_REDIRECT_URI || '',
          client_id: process.env.LINKEDIN_CLIENT_ID || '',
          client_secret: process.env.LINKEDIN_CLIENT_SECRET || '',
        }),
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        },
      );

      const { access_token, expires_in } = tokenResponse.data;
      const expiresAt = new Date(Date.now() + expires_in * 1000);

      // Fetch profile info
      const profileRes = await axios.get('https://api.linkedin.com/v2/userinfo', {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      const profile = profileRes.data;

      // Extract userId from state (format: linkedin-{userId}-{timestamp})
      const stateParts = state.split('-');
      const userId = stateParts.length >= 2 ? stateParts[1] : null;

      if (!userId) {
        throw new UnauthorizedException('Invalid state parameter');
      }

      // Find user by ID
      const user = await this.userModel.findById(userId);
      if (!user) {
        throw new UnauthorizedException('User not found');
      }

      // Save token
      user.connectedAccounts = {
        ...user.connectedAccounts,
        linkedin: {
          accessToken: access_token,
          expiresAt,
          profile,
        },
      };
      await user.save();

      return { message: 'LinkedIn connected successfully', profile };
    } catch (err) {
      console.error('LinkedIn callback error:', err.response?.data || err.message);
      throw new InternalServerErrorException('LinkedIn auth failed');
    }
  }

  /**
   * Get connection status
   */
  async getConnectionStatus(userId: string) {
    const user = await this.userModel.findById(userId);
    if (!user) {
      throw new NotFoundException('User not found');
    }

    const linkedInAccount = user.connectedAccounts?.linkedin;
    const isConnected = !!(
      linkedInAccount?.accessToken && 
      linkedInAccount?.expiresAt && 
      new Date(linkedInAccount.expiresAt) > new Date()
    );

    return {
      isConnected,
      profile: linkedInAccount?.profile || null,
      expiresAt: linkedInAccount?.expiresAt || null,
    };
  }

  /**
   * Get user's LinkedIn access token
   */
  private async getAccessToken(userId: string): Promise<{ token: string; profile: any }> {
    const user = await this.userModel.findById(userId);
    if (!user) {
      throw new UnauthorizedException('User not found');
    }

    const linkedInAccount = user.connectedAccounts?.linkedin;
    if (!linkedInAccount?.accessToken) {
      throw new UnauthorizedException('LinkedIn not connected. Please connect your LinkedIn account first.');
    }

    // Check if token is expired
    if (linkedInAccount.expiresAt && new Date(linkedInAccount.expiresAt) <= new Date()) {
      throw new UnauthorizedException('LinkedIn token expired. Please reconnect your account.');
    }

    return {
      token: linkedInAccount.accessToken,
      profile: linkedInAccount.profile,
    };
  }

  /**
   * Post simple text to LinkedIn
   */
  async postText(userId: string, text: string) {
    const { token, profile } = await this.getAccessToken(userId);
    const authorUrn = `urn:li:person:${profile.sub}`;

    try {
      const response = await axios.post(
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

      return {
        message: '✅ Posted successfully to LinkedIn!',
        content: text,
        postId: response.data.id,
      };
    } catch (error) {
      console.error('LinkedIn post error:', error.response?.data || error.message);
      throw new InternalServerErrorException(
        `Failed to post to LinkedIn: ${error.response?.data?.message || error.message}`
      );
    }
  }

  /**
   * Upload image to LinkedIn and get asset URN
   */
  private async uploadImageToLinkedIn(token: string, imageBuffer: Buffer, userId: string): Promise<string> {
    try {
      // Step 1: Register upload
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

      // Step 2: Upload image
      await axios.put(uploadUrl, imageBuffer, {
        headers: {
          'Content-Type': 'image/jpeg',
        },
      });

      return asset;
    } catch (error) {
      console.error('LinkedIn image upload error:', error.response?.data || error.message);
      throw new InternalServerErrorException('Failed to upload image to LinkedIn');
    }
  }

  /**
   * Post to LinkedIn with an image
   */
  async postWithImage(userId: string, text: string, imageFile: any) {
    const { token, profile } = await this.getAccessToken(userId);
    const authorUrn = `urn:li:person:${profile.sub}`;

    try {
      // Ensure imageBuffer is a Buffer
      const imageBuffer = Buffer.isBuffer(imageFile.buffer) 
        ? imageFile.buffer 
        : Buffer.from(imageFile.buffer);

      const asset = await this.uploadImageToLinkedIn(token, imageBuffer, profile.sub);

      // Post with image
      const response = await axios.post(
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

      return {
        message: '✅ Posted successfully to LinkedIn with image!',
        content: text,
        postId: response.data.id,
      };
    } catch (error) {
      console.error('LinkedIn post with image error:', error.response?.data || error.message);
      throw new InternalServerErrorException(
        `Failed to post to LinkedIn: ${error.response?.data?.message || error.message}`
      );
    }
  }

  /**
   * Generate and post using AI
   */
  async postWithAI(userId: string, topic: string, includeImage: boolean = false) {
    try {
      // Generate post content
      const postContent = await this.aiService.generateLinkedInPostWithImage(topic, includeImage);
      
      // Combine text and hashtags
      const fullText = postContent.hashtags.length > 0
        ? `${postContent.text}\n\n${postContent.hashtags.join(' ')}`
        : postContent.text;

      if (includeImage && postContent.imageBuffer) {
        // Create a temporary file-like object for the image
        const imageFile = {
          buffer: postContent.imageBuffer,
          mimetype: 'image/jpeg',
          originalname: 'ai-generated-image.jpg',
        };

        return await this.postWithImage(userId, fullText, imageFile);
      } else {
        return await this.postText(userId, fullText);
      }
    } catch (error) {
      console.error('AI post generation error:', error);
      throw new InternalServerErrorException(`Failed to generate and post: ${error.message}`);
    }
  }

  /**
   * Create a scheduled post
   */
  async createScheduledPost(userId: string, dto: CreateScheduledPostDto) {
    // Validate cron expression (basic validation)
    const cronRegex = /^(\*|([0-9]|[1-5][0-9])|\*\/([0-9]|[1-5][0-9])) (\*|([0-9]|1[0-9]|2[0-3])|\*\/([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|[12][0-9]|3[01])|\*\/([1-9]|[12][0-9]|3[01])) (\*|([1-9]|1[0-2])|\*\/([1-9]|1[0-2])) (\*|([0-6])|\*\/([0-6]))$/;
    if (!cronRegex.test(dto.schedule)) {
      throw new BadRequestException('Invalid cron expression format. Use format: "minute hour day month dayOfWeek"');
    }

    try {
      // Calculate next post time using cron parser with IST timezone
      const { CronExpressionParser } = require('cron-parser');
      const timezone = process.env.TZ || 'Asia/Kolkata';
      
      // Parse with current time in IST context
      const interval = CronExpressionParser.parse(dto.schedule, {
        tz: timezone,
      });
      
      // Get next execution time (returns UTC Date object representing IST time)
      const nextPostAt = interval.next().toDate();
      
      // Log for debugging
      console.log(`Schedule created: ${dto.schedule}`);
      console.log(`Next post at (UTC): ${nextPostAt.toISOString()}`);
      console.log(`Next post at (IST): ${nextPostAt.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}`);

      const scheduledPost = new this.scheduledPostModel({
        userId,
        topic: dto.topic,
        customText: dto.customText,
        schedule: dto.schedule,
        includeImage: dto.includeImage || false,
        isActive: true,
        nextPostAt,
        postCount: 0,
      });

      const saved = await scheduledPost.save();
      return {
        message: 'Scheduled post created successfully',
        schedule: saved,
      };
    } catch (error) {
      console.error('Error creating scheduled post:', error);
      throw new BadRequestException(`Failed to create scheduled post: ${error.message}`);
    }
  }

  /**
   * Get all scheduled posts for user
   */
  async getScheduledPosts(userId: string) {
    return this.scheduledPostModel.find({ userId }).sort({ createdAt: -1 });
  }

  /**
   * Activate a schedule
   */
  async activateSchedule(userId: string, scheduleId: string) {
    const schedule = await this.scheduledPostModel.findOne({
      _id: scheduleId,
      userId,
    });

    if (!schedule) {
      throw new NotFoundException('Schedule not found');
    }

    schedule.isActive = true;
    if (!schedule.nextPostAt) {
      const { CronExpressionParser } = require('cron-parser');
      const timezone = process.env.TZ || 'Asia/Kolkata';
      const interval = CronExpressionParser.parse(schedule.schedule, {
        tz: timezone,
      });
      schedule.nextPostAt = interval.next().toDate();
    }
    await schedule.save();

    return {
      message: 'Schedule activated successfully',
      schedule,
    };
  }

  /**
   * Deactivate a schedule
   */
  async deactivateSchedule(userId: string, scheduleId: string) {
    const schedule = await this.scheduledPostModel.findOne({
      _id: scheduleId,
      userId,
    });

    if (!schedule) {
      throw new NotFoundException('Schedule not found');
    }

    schedule.isActive = false;
    await schedule.save();

    return {
      message: 'Schedule deactivated successfully',
      schedule,
    };
  }

  /**
   * Delete a schedule
   */
  async deleteSchedule(userId: string, scheduleId: string) {
    const result = await this.scheduledPostModel.deleteOne({
      _id: scheduleId,
      userId,
    });

    if (result.deletedCount === 0) {
      throw new NotFoundException('Schedule not found');
    }

    return {
      message: 'Schedule deleted successfully',
    };
  }
}