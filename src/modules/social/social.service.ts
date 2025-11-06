import { Injectable, UnauthorizedException, BadRequestException } from '@nestjs/common';
import axios from 'axios';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User } from '../user/schemas/user.schema';
import { LinkedInService } from '../linkedin/linkedin.service';

@Injectable()
export class SocialService {
  constructor(@InjectModel(User.name) private userModel: Model<User>,
 private linkedInService: LinkedInService

) {}

  // ----------------- LINKEDIN -----------------
  getLinkedInAuthUrl(userId: string) {
    return this.linkedInService.generateAuthUrl(userId);
  }

  handleLinkedInCallback(code: string, state: string) {
    return this.linkedInService.handleCallback(code, state);
  }

  async postToLinkedIn(userId: string, text: string) {
    const user = await this.userModel.findById(userId);
    if (!user) {
      throw new UnauthorizedException('User not found');
    }
    const token = user.connectedAccounts?.linkedin?.accessToken;
    const profile = user.connectedAccounts?.linkedin?.profile;

    if (!token || !profile?.sub) {
      throw new UnauthorizedException('LinkedIn not connected or profile missing.');
    }

    const authorUrn = `urn:li:person:${profile.sub}`;

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
      { headers: { Authorization: `Bearer ${token}` } },
    );

    return { message: '✅ Posted successfully to LinkedIn!', content: text };
  }

  // ----------------- TWITTER -----------------
  getTwitterAuthUrl() {
    const clientId = process.env.TWITTER_CLIENT_ID;
    const redirectUri = process.env.TWITTER_REDIRECT_URI;
    const scope = 'tweet.read tweet.write users.read offline.access';
    const state = 'sociantra-twitter-' + Date.now();

    const authUrl = `https://twitter.com/i/oauth2/authorize?response_type=code&client_id=${clientId}&redirect_uri=${redirectUri}&scope=${encodeURIComponent(scope)}&state=${state}&code_challenge=challenge&code_challenge_method=plain`;
    return { authUrl };
  }

  async handleTwitterCallback(code: string) {
    try {
      const tokenRes = await axios.post(
        'https://api.twitter.com/2/oauth2/token',
        new URLSearchParams({
          code,
          grant_type: 'authorization_code',
          redirect_uri: process.env.TWITTER_REDIRECT_URI || '',
          client_id: process.env.TWITTER_CLIENT_ID || '',
          code_verifier: 'challenge',
        }),
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
      );

      const { access_token, refresh_token, expires_in } = tokenRes.data;
      const expiresAt = new Date(Date.now() + expires_in * 1000);

      const userId = 'USER_ID_HERE';
      await this.userModel.findByIdAndUpdate(userId, {
        'connectedAccounts.twitter': {
          accessToken: access_token,
          refreshToken: refresh_token,
          expiresAt,
        },
      });

      return { message: 'Twitter connected successfully', expiresAt };
    } catch (err) {
      throw new UnauthorizedException('Twitter auth failed');
    }
  }

  // ----------------- WHATSAPP -----------------
  async sendWhatsAppMessage(to: string, text: string) {
    if (!process.env.WHATSAPP_TOKEN || !process.env.WHATSAPP_PHONE_NUMBER_ID)
      throw new BadRequestException('WhatsApp credentials not configured');

    const url = `${process.env.WHATSAPP_API_URL}/${process.env.WHATSAPP_PHONE_NUMBER_ID}/messages`;

    await axios.post(
      url,
      {
        messaging_product: 'whatsapp',
        to,
        type: 'text',
        text: { body: text },
      },
      {
        headers: {
          Authorization: `Bearer ${process.env.WHATSAPP_TOKEN}`,
          'Content-Type': 'application/json',
        },
      },
    );

    return { message: `Message sent to ${to}` };
  }
}
