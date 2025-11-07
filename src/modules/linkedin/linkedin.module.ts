import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { LinkedInService } from './linkedin.service';
import { LinkedInController } from './linkedin.controller';
import { User, UserSchema } from '../user/schemas/user.schema';
import { ScheduledPost, ScheduledPostSchema } from './schemas/scheduled-post.schema';
import { AIModule } from '../ai/ai.module';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: User.name, schema: UserSchema },
      { name: ScheduledPost.name, schema: ScheduledPostSchema },
    ]),
    AIModule,
  ],
  controllers: [LinkedInController],
  providers: [LinkedInService],
  exports: [LinkedInService],
})
export class LinkedInModule {}

