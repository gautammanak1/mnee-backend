import { Controller, Get, Query, Req, UseGuards, Post, Body } from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { SocialService } from './social.service';
import { JwtAuthGuard } from '../auth/guards/jwt.guard';
import { SendMessageDto } from './dto/send-message.dto';

@ApiTags('Social Connections')
@Controller('social')
export class SocialController {
  constructor(private readonly socialService: SocialService) {}

  // ----------------- LINKEDIN -----------------
 @Get('linkedin/connect')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Redirect user to LinkedIn OAuth' })
  getLinkedInUrl(@Req() req) {
    const userId = req.user.userId;
    return this.socialService.getLinkedInAuthUrl(userId);
  }

    @Get('linkedin/callback')
  @ApiOperation({ summary: 'LinkedIn OAuth callback handler' })
  async linkedinCallback(@Query('code') code: string, @Query('state') state: string) {
    return this.socialService.handleLinkedInCallback(code, state);
  }

  // ----------------- TWITTER -----------------
  @Get('twitter/connect')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Get Twitter OAuth URL' })
  getTwitterAuthUrl() {
    return this.socialService.getTwitterAuthUrl();
  }

   @Post('linkedin/post')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Post text content to LinkedIn' })
  async postLinkedIn(@Req() req, @Body() body: { text: string }) {
    return this.socialService.postToLinkedIn(req.user.userId, body.text);
  }

  @Get('twitter/callback')
  @ApiOperation({ summary: 'Twitter OAuth callback' })
  async twitterCallback(@Query('code') code: string) {
    return this.socialService.handleTwitterCallback(code);
  }

  // ----------------- WHATSAPP -----------------
  @Post('whatsapp/send')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Send WhatsApp message via Meta API' })
  async sendWhatsApp(@Body() body: SendMessageDto) {
    return this.socialService.sendWhatsAppMessage(body.to, body.text);
  }
}
