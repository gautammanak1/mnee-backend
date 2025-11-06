import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { User, UserSchema } from '../user/schemas/user.schema';
import { SocialService } from './social.service';
import { SocialController } from './social.controller';
import { LinkedInService } from '../linkedin/linkedin.service';


@Module({
  imports: [MongooseModule.forFeature([{ name: User.name, schema: UserSchema }])],
  controllers: [SocialController],
  providers: [SocialService, LinkedInService],
})
export class SocialModule {}
