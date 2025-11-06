import { Controller, Get, Post, Req, Res, HttpStatus } from '@nestjs/common';
import { WhatsAppService } from './whatsapp.service';
import { Response, Request } from 'express';

@Controller('whatsapp')
export class WhatsAppController {
  constructor(private readonly waService: WhatsAppService) {}

  // webhook verification (Meta requirement)

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


  // handle incoming messages
  @Post('webhook')
  async receive(@Req() req: Request, @Res() res: Response) {
    try {
        console.log("1232435454")
      const body = req.body;
      if (body.object) {
        const entry = body.entry?.[0];
        const changes = entry?.changes?.[0];
        const message = changes?.value?.messages?.[0];

        if (message && message.text) {
          const from = message.from; // sender phone
          const text = message.text.body;
          await this.waService.handleIncomingMessage(from, text);
        }
      }
      return res.sendStatus(200);
    } catch (e) {
      console.error('Webhook error:', e);
      return res.sendStatus(500);
    }
  }
}
