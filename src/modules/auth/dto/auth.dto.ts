import { ApiProperty } from '@nestjs/swagger';
import { IsEmail, IsNotEmpty, MinLength } from 'class-validator';

export class SignupDto {
  @ApiProperty({ example: 'Ashish' })
  @IsNotEmpty()
  name: string;

  @ApiProperty({ example: 'ashish@example.com' })
  @IsEmail()
  email: string;

  @ApiProperty({ example: 'test1234', minLength: 6 })
  @MinLength(6)
  password: string;
}

export class LoginDto {
  @ApiProperty({ example: 'ashish@example.com' })
  @IsEmail()
  email: string;

  @ApiProperty({ example: 'test1234', minLength: 6 })
  @MinLength(6)
  password: string;
}
