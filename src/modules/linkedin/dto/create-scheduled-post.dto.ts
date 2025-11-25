import { ApiProperty } from '@nestjs/swagger';
import { IsString, IsNotEmpty, IsOptional, IsBoolean } from 'class-validator';

export class CreateScheduledPostDto {
  @ApiProperty({ example: 'AI trends in 2025' })
  @IsString()
  @IsNotEmpty()
  topic: string;

  @ApiProperty({ 
    example: '0 9 * * 1', 
    description: 'Cron expression for recurring schedule (e.g., "0 9 * * 1" for every Monday at 9 AM)' 
  })
  @IsString()
  @IsNotEmpty()
  schedule: string;

  @ApiProperty({ example: true, required: false })
  @IsBoolean()
  @IsOptional()
  includeImage?: boolean;

  @ApiProperty({ example: 'My custom post text', required: false })
  @IsString()
  @IsOptional()
  customText?: string;
}

