import { Injectable, UnauthorizedException, InternalServerErrorException } from '@nestjs/common';
import axios from 'axios';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { User } from '../user/schemas/user.schema';


@Injectable()
export class LinkedInService {
  constructor(@InjectModel(User.name) private userModel: Model<User>) {}

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

      const email = profile.email || profile.email_verified || profile.sub;

      // Find user by email
      const user = await this.userModel.findOne({ email });
      if (!user) {
        throw new UnauthorizedException('No user found for LinkedIn email');
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
}
