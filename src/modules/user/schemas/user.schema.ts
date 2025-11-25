import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { Document } from 'mongoose';

@Schema({ timestamps: true })
export class User extends Document {
  @Prop({ required: true })
  name: string;

  @Prop({ unique: true, required: true })
  email: string;

  @Prop({ select: false })
  password?: string;

  @Prop()
  provider: 'local' | 'google';

  @Prop()
  googleId?: string;

  @Prop()
  dbName: string; // <-- important: user's DB

  @Prop()
  profileImage?: string;

  @Prop()
  refreshToken?: string;

  @Prop({
  type: {
    linkedin: {
      accessToken: String,
      expiresAt: Date,
      profile: Object,
    },
    twitter: {
      accessToken: String,
      refreshToken: String,
      expiresAt: Date,
    },
    whatsapp: {
      accessToken: String,
      phoneNumberId: String,
    },
  },
  default: {},
})
connectedAccounts: Record<string, any>;


}

export const UserSchema = SchemaFactory.createForClass(User);
