// src/modules/instagram/instagram.controller.ts
import { Controller, Get, Post, Req, Res, HttpStatus } from '@nestjs/common';
import { Response, Request } from 'express';
import { InstagramService } from './instagram.service';

@Controller('instagram')
export class InstagramController {
  constructor(private readonly igService: InstagramService) {}

  @Get('webhook')
  verify(@Req() req: Request, @Res() res: Response) {
    const VERIFY_TOKEN = process.env.VERIFY_TOKEN;
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    console.log('VERIFY_TOKEN from .env:', VERIFY_TOKEN);
    console.log('Incoming token:', token);
    console.log('Incoming mode:', mode);

    if (mode && token && mode === 'subscribe' && token === VERIFY_TOKEN) {
      console.log('✅ Webhook verified by Meta!');
      return res.status(HttpStatus.OK).send(challenge);
    } else {
      console.log('❌ Webhook verification failed.');
      return res.sendStatus(HttpStatus.FORBIDDEN);
    }
  }

  @Post('webhook')
  async receive(@Req() req: Request, @Res() res: Response) {
    const body = req.body;
    console.log('Received webhook payload:', JSON.stringify(body, null, 2));

    if (body.object === 'instagram' && body.entry) {
      for (const entry of body.entry) {
        const messaging = entry.messaging;
        if (messaging) {
          for (const event of messaging) {
            // Fallback for test payloads missing sender/recipient
            const from = event.sender?.id || 'unknown (likely test event)';
            const to = event.recipient?.id || entry.id; // Fallback to entry.id for business ID

            if (event.message) {
              const text = event.message.text;
              const mid = event.message.mid;
              const attachments = event.message.attachments;
              console.log(`Received message from ${from} to ${to}: ${text || 'Attachment/Other'} (MID: ${mid})`);
              if (text) {
                await this.igService.handleMessage(from, text);
              } else if (attachments) {
                // Handle attachments (e.g., images, videos)
                console.log('Attachments:', attachments);
                // Add logic in service if needed
              }
            } else if (event.read) {
              const mid = event.read.mid;
              console.log(`Message read by ${from} (MID: ${mid})`);
              // Optional: Update message status in your DB via service
              await this.igService.handleRead(from, mid);
            } else if (event.reaction) {
              console.log(`Reaction from ${from}: ${event.reaction.reaction} on MID ${event.reaction.mid}`);
              // Handle reactions
            } else if (event.postback) {
              console.log(`Postback from ${from}: Payload ${event.postback.payload}`);
              // Handle button clicks or icebreakers
            } else {
              console.log('Unhandled event:', JSON.stringify(event, null, 2));
            }
          }
        }
      }
    } else {
      console.log('Invalid payload structure.');
    }

    return res.sendStatus(200); // Acknowledge to avoid retries from Meta
  }
}