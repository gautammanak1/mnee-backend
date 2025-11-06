import { Module } from '@nestjs/common';
import { WhatsAppService } from './whatsapp.service';
import { WhatsAppController } from './whatsapp.controller';
import { GeminiService } from './gemini.service';

@Module({
  controllers: [WhatsAppController],
  providers: [WhatsAppService, GeminiService],
})
export class WhatsAppModule {}
