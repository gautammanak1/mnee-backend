import { Injectable } from '@nestjs/common';
import axios from 'axios';
import { GeminiService } from './gemini.service';

@Injectable()
export class WhatsAppService {
  constructor(private readonly gemini: GeminiService) {}

  async handleIncomingMessage(from: string, text: string) {
    console.log('📥 Received:', text);
    const reply = await this.gemini.generateReply(text);
    console.log('🤖 Reply:', reply);
    await this.sendWhatsAppMessage(from, reply);
  }

  async sendWhatsAppMessage(to: string, message: string) {
    const url = `https://graph.facebook.com/v21.0/${process.env.WHATSAPP_PHONE_NUMBER_ID}/messages`;
    await axios.post(
      url,
      {
        messaging_product: 'whatsapp',
        to,
        text: { body: message },
      },
      {
        headers: {
          Authorization: `Bearer ${process.env.WHATSAPP_ACCESS_TOKEN}`,
          'Content-Type': 'application/json',
        },
      },
    );
  }
}
