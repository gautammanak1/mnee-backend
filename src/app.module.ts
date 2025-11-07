import {
  Module,
  MiddlewareConsumer,
  NestModule,
  RequestMethod,
} from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { MongooseModule } from '@nestjs/mongoose';

import { AuthModule } from './modules/auth/auth.module';
import { TasksModule } from './modules/tasks/task.module';
import { TenantModule } from './modules/tenant/tenant.module';
import { SocialModule } from './modules/social/social.module';
import { WhatsAppModule } from './modules/whatsapp/whatsapp.module';
import { InstagramModule } from './modules/instagram/instagram.module';
import { LinkedInModule } from './modules/linkedin/linkedin.module';
import { AIModule } from './modules/ai/ai.module';
import { SchedulerModule } from './modules/scheduler/scheduler.module';

@Module({
  imports: [
    // Global config
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env'],
    }),

    // Root connection to MAIN DB (stores users + metadata)
    MongooseModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: (config: ConfigService) => ({
        uri:
          config.get<string>('MONGO_URI') ||
          'mongodb://localhost:27017/sociantra',
        // Optional: add recommended options here
        // serverSelectionTimeoutMS: 5000,
        // maxPoolSize: 10,
      }),
      inject: [ConfigService],
    }),
    TenantModule,
    SocialModule,
    // Feature modules
    AuthModule,
    TasksModule,
    WhatsAppModule,
    InstagramModule,
    // LinkedIn Automation modules
    AIModule,
    LinkedInModule,
    SchedulerModule,
  ],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    // Ensure tenant DB connections are warmed for authenticated requests
    // consumer
  }
}
