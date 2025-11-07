import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { ScheduleModule } from '@nestjs/schedule';
import { SchedulerService } from './scheduler.service';
import { ScheduledPost, ScheduledPostSchema } from '../linkedin/schemas/scheduled-post.schema';
import { User, UserSchema } from '../user/schemas/user.schema';
import { AIModule } from '../ai/ai.module';

@Module({
  imports: [
    ScheduleModule.forRoot(),
    MongooseModule.forFeature([
      { name: ScheduledPost.name, schema: ScheduledPostSchema },
      { name: User.name, schema: UserSchema },
    ]),
    AIModule,
  ],
  providers: [SchedulerService],
  exports: [SchedulerService],
})
export class SchedulerModule {}

