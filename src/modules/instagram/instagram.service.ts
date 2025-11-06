// src/modules/instagram/instagram.service.ts
import { Injectable, Logger, HttpException, HttpStatus } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { lastValueFrom } from 'rxjs';
import { GeminiService } from '../whatsapp/gemini.service'; // Assuming this is correctly set up
import axios from 'axios';

@Injectable()
export class InstagramService {
  private readonly logger = new Logger(InstagramService.name);
  private readonly apiUrl = 'https://graph.facebook.com/v21.0/me/messages';
  private readonly accessToken = process.env.IG_PAGE_ACCESS_TOKEN;

  constructor(
   
    private readonly geminiService: GeminiService,
  ) {
    if (!this.accessToken) {
      this.logger.error('IG_PAGE_ACCESS_TOKEN is not set in .env');
    }
  }

  async handleMessage(from: string, text: string, attachments?: any[]): Promise<void> {
    try {
      this.logger.log(`📥 Received message from ${from}: ${text || 'Attachment/Other'}`);
      
      // Optional: Handle attachments (e.g., images, videos) if present
      // if (attachments) {
      //   this.logger.log(`Attachments received: ${JSON.stringify(attachments)}`);
      //   // Add custom logic, e.g., download/process via Gemini or reply accordingly
      // }

      const reply = await this.geminiService.generateReply(text);
      this.logger.log(`🤖 Generated reply: ${reply}`);
      
      await this.sendMessage(from, reply);
    } catch (error) {
      this.logger.error(`Error handling message from ${from}: ${error.message}`);
      // Optional: Send fallback reply to user
      await this.sendMessage(from, 'Sorry, something went wrong. Please try again!');
      throw new HttpException('Message handling failed', HttpStatus.INTERNAL_SERVER_ERROR);
    }
  }

  async handleRead(from: string, mid: string): Promise<void> {
    try {
      this.logger.log(`📖 Read receipt for MID ${mid} by ${from}`);
      // Optional: Update your database or track analytics here
      // e.g., await this.someRepo.updateMessageStatus(mid, 'read');
    } catch (error) {
      this.logger.error(`Error handling read receipt: ${error.message}`);
    }
  }

  private async sendMessage(to: string, text: string): Promise<void> {
    if (!this.accessToken) {
      throw new Error('Missing IG_PAGE_ACCESS_TOKEN');
    }

    const payload = {
      recipient: { id: to },
      message: { text },
      messaging_type: 'RESPONSE',
    };

    try {
      const response:any = await  axios.post(`${this.apiUrl}?access_token=${this.accessToken}`, payload);
      
      this.logger.log(`✅ Message sent to ${to}: ${text} (Response: ${response.status})`);
    } catch (error) {
      this.logger.error(`❌ Error sending message to ${to}: ${error.response?.data?.error?.message || error.message}`);
      throw error;
    }
  }

  // Optional: Add methods for advanced features
  // async sendImage(to: string, imageUrl: string): Promise<void> {
  //   // Similar to sendMessage, but with message.attachment = { type: 'image', payload: { url: imageUrl } }
  // }
}