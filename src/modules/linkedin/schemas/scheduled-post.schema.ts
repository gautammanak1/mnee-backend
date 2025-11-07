import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

@Schema({ timestamps: true })
export class ScheduledPost extends Document {
  @Prop({ required: true })
  userId: string;

  @Prop({ required: true })
  topic: string;

  @Prop()
  customText?: string;

  @Prop({ required: true })
  schedule: string; // Cron expression

  @Prop({ default: true })
  includeImage: boolean;

  @Prop({ default: true })
  isActive: boolean;

  @Prop()
  lastPostedAt?: Date;

  @Prop()
  nextPostAt?: Date;

  @Prop({ default: 0 })
  postCount: number;
}

export const ScheduledPostSchema = SchemaFactory.createForClass(ScheduledPost);

