import { ApiProperty } from '@nestjs/swagger';
import { IsString, IsNotEmpty } from 'class-validator';

export class SendMessageDto {
  @ApiProperty({ example: '919876543210', description: 'Recipient WhatsApp number with country code' })
  @IsString()
  @IsNotEmpty()
  to: string;

  @ApiProperty({ example: 'Hello from Sociantra!' })
  @IsString()
  @IsNotEmpty()
  text: string;
}
