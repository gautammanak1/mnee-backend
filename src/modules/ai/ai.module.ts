import { Module } from '@nestjs/common';
import { AIService } from './ai.service';
import { GeminiService } from '../whatsapp/gemini.service';

@Module({
  providers: [AIService, GeminiService],
  exports: [AIService],
})
export class AIModule {}

