import {
  Controller,
  Post,
  Body,
  Get,
  Req,
  UseGuards,
} from '@nestjs/common';
import { AuthService } from './auth.service';
import { JwtAuthGuard } from './guards/jwt.guard';
import { GoogleAuthGuard } from './guards/google.guard';
import { ApiBearerAuth, ApiTags, ApiOperation, ApiResponse, ApiBody } from '@nestjs/swagger';
import { SignupDto, LoginDto } from './dto/auth.dto';

@ApiTags('Auth')
@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  // ✅ Signup
  @Post('signup')
  @ApiOperation({ summary: 'Register a new user (Email/Password)' })
  @ApiBody({ type: SignupDto })
  @ApiResponse({ status: 201, description: 'User registered successfully' })
  @ApiResponse({ status: 400, description: 'User already exists' })
  signup(@Body() body: SignupDto) {
    return this.authService.signup(body.name, body.email, body.password);
  }

  // ✅ Login
  @Post('login')
  @ApiOperation({ summary: 'Login with email and password' })
  @ApiBody({ type: LoginDto })
  @ApiResponse({ status: 200, description: 'Returns access token' })
  @ApiResponse({ status: 401, description: 'Invalid credentials' })
  login(@Body() body: LoginDto) {
    return this.authService.login(body.email, body.password);
  }

  // ✅ Google OAuth
  @Get('google')
  @ApiOperation({ summary: 'Redirect to Google login' })
  @ApiResponse({ status: 302, description: 'Redirects to Google OAuth2' })
  @UseGuards(GoogleAuthGuard)
  async googleAuth() {}

  @Get('google/callback')
  @ApiOperation({ summary: 'Google OAuth callback' })
  @ApiResponse({ status: 200, description: 'Returns access token after Google login' })
  @UseGuards(GoogleAuthGuard)
  async googleAuthRedirect(@Req() req) {
    return this.authService.googleLogin(req.user);
  }

  // ✅ Protected route
  @Get('me')
  @ApiBearerAuth()
  @UseGuards(JwtAuthGuard)
  @ApiOperation({ summary: 'Get logged-in user profile (JWT protected)' })
  @ApiResponse({ status: 200, description: 'Returns user info' })
  getProfile(@Req() req) {
    return req.user;
  }
}
