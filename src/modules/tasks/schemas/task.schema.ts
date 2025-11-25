import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

@Schema({ timestamps: true })
export class Task extends Document {
  @Prop()
  userId: string;

  @Prop()
  topic: string;

  @Prop()
  caption: string;

  @Prop([String])
  hashtags: string[];

  @Prop()
  imageUrl: string;

  @Prop()
  platform: string;

  @Prop()
  scheduledAt: Date;

  @Prop({ default: 'draft' })
  status: string;
}

export const TaskSchema = SchemaFactory.createForClass(Task);
