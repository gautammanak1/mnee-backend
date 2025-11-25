import { ApiProperty } from '@nestjs/swagger';
import { IsString, IsNotEmpty, IsDateString, IsOptional, IsArray, IsIn } from 'class-validator';

export class CreateTaskDto {
  @ApiProperty({ example: 'AI trends 2025' })
  @IsString()
  @IsNotEmpty()
  topic: string;

  @ApiProperty({ example: 'Exploring the latest AI tools for developers' })
  @IsString()
  @IsOptional()
  caption?: string;

  @ApiProperty({ example: ['#AI', '#Technology'], type: [String] })
  @IsArray()
  @IsOptional()
  hashtags?: string[];

  @ApiProperty({ example: 'linkedin', enum: ['linkedin', 'twitter'] })
  @IsIn(['linkedin', 'twitter'])
  platform: string;

  @ApiProperty({ example: '2025-11-05T10:00:00Z' })
  @IsDateString()
  scheduledAt: string;
}
