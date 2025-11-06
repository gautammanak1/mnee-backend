import { Module } from '@nestjs/common';
import { InstagramController } from './instagram.controller';
import { InstagramService } from './instagram.service';
import { GeminiService } from '../whatsapp/gemini.service';
import { HttpService } from '@nestjs/axios';

@Module({
  controllers: [InstagramController],
  providers: [InstagramService,GeminiService],
  exports: [InstagramService],
})
export class InstagramModule {}
