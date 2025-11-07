import {
  Controller,
  Get,
  Post,
  Body,
  Query,
  Param,
  Req,
  UseGuards,
  UseInterceptors,
  UploadedFile,
} from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags, ApiConsumes, ApiBody } from '@nestjs/swagger';
import { FileInterceptor } from '@nestjs/platform-express';
import { LinkedInService } from './linkedin.service';
import { JwtAuthGuard } from '../auth/guards/jwt.guard';
import { CreateLinkedInPostDto } from './dto/create-linkedin-post.dto';
import { CreateScheduledPostDto } from './dto/create-scheduled-post.dto';

@ApiTags('LinkedIn Automation')
@Controller('linkedin')
export class LinkedInController {
  constructor(private readonly linkedInService: LinkedInService) {}

  @Get('connect')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Get LinkedIn OAuth URL to connect account' })
  getLinkedInAuthUrl(@Req() req) {
    const userId = req.user.userId;
    return this.linkedInService.generateAuthUrl(userId);
  }

  @Get('callback')
  @ApiOperation({ summary: 'LinkedIn OAuth callback handler' })
  async handleCallback(@Query('code') code: string, @Query('state') state: string) {
    try {
      const result = await this.linkedInService.handleCallback(code, state);
      return {
        ...result,
        redirectUrl: process.env.FRONTEND_URL || 'http://localhost:3000',
      };
    } catch (error) {
      return {
        error: error.message,
        redirectUrl: `${process.env.FRONTEND_URL || 'http://localhost:3000'}/linkedin/error`,
      };
    }
  }

  @Get('status')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Check if LinkedIn is connected' })
  async getConnectionStatus(@Req() req) {
    const userId = req.user.userId;
    return this.linkedInService.getConnectionStatus(userId);
  }

  @Post('post')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Post a simple text post to LinkedIn' })
  async postToLinkedIn(@Req() req, @Body() dto: CreateLinkedInPostDto) {
    const userId = req.user.userId;
    return this.linkedInService.postText(userId, dto.text);
  }

  @Post('post-with-ai')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Generate and post a LinkedIn post using AI based on topic' })
  async postWithAI(@Req() req, @Body() dto: { topic: string; includeImage?: boolean }) {
    const userId = req.user.userId;
    return this.linkedInService.postWithAI(userId, dto.topic, dto.includeImage || false);
  }

  @Post('post-with-image')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiConsumes('multipart/form-data')
  @ApiBody({
    schema: {
      type: 'object',
      properties: {
        text: { type: 'string' },
        image: {
          type: 'string',
          format: 'binary',
        },
      },
    },
  })
  @UseInterceptors(FileInterceptor('image'))
  @ApiOperation({ summary: 'Post to LinkedIn with an image' })
  
  async postWithImage(
    @Req() req,
    @Body() body: { text: string },
    @UploadedFile() file: Express.Multer.File,
  ) {
    const userId = req.user.userId;
    return this.linkedInService.postWithImage(userId, body.text, file);
  }

  @Post('schedule')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Create a recurring scheduled post task' })
  async createScheduledPost(@Req() req, @Body() dto: CreateScheduledPostDto) {
    const userId = req.user.userId;
    return this.linkedInService.createScheduledPost(userId, dto);
  }

  @Get('schedules')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Get all scheduled posts for the user' })
  async getScheduledPosts(@Req() req) {
    const userId = req.user.userId;
    return this.linkedInService.getScheduledPosts(userId);
  }

  @Post('schedules/:id/activate')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Activate a scheduled post' })
  async activateSchedule(@Req() req, @Param('id') id: string) {
    const userId = req.user.userId;
    return this.linkedInService.activateSchedule(userId, id);
  }

  @Post('schedules/:id/deactivate')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Deactivate a scheduled post' })
  async deactivateSchedule(@Req() req, @Param('id') id: string) {
    const userId = req.user.userId;
    return this.linkedInService.deactivateSchedule(userId, id);
  }

  @Post('schedules/:id/delete')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Delete a scheduled post' })
  async deleteSchedule(@Req() req, @Param('id') id: string) {
    const userId = req.user.userId;
    return this.linkedInService.deleteSchedule(userId, id);
  }
}

