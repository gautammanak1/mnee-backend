import { ApiProperty } from '@nestjs/swagger';
import { IsString, IsNotEmpty } from 'class-validator';

export class CreateLinkedInPostDto {
  @ApiProperty({ example: 'Excited to share my latest insights on AI and automation!' })
  @IsString()
  @IsNotEmpty()
  text: string;
}

