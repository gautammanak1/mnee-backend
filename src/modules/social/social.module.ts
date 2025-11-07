import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { User, UserSchema } from '../user/schemas/user.schema';
import { SocialService } from './social.service';
import { SocialController } from './social.controller';
import { LinkedInModule } from '../linkedin/linkedin.module';
import { AIModule } from '../ai/ai.module';

@Module({
  imports: [
    MongooseModule.forFeature([{ name: User.name, schema: UserSchema }]),
    LinkedInModule,
    AIModule,
  ],
  controllers: [SocialController],
  providers: [SocialService],
})
export class SocialModule {}
