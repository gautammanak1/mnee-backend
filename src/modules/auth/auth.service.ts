import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import * as bcrypt from 'bcryptjs';
import { User } from '../user/schemas/user.schema';
import { TenantConnectionService } from '../tenant/tenant-connection.service';

@Injectable()
export class AuthService {
  constructor(
    @InjectModel(User.name) private userModel: Model<User>,
    private jwtService: JwtService,
    private tenantConnectionService: TenantConnectionService,
  ) {}

  async signup(name: string, email: string, password: string) {
    const exists = await this.userModel.findOne({ email });
    if (exists) throw new UnauthorizedException('User already exists');

    const hashed = await bcrypt.hash(password, 10);

    const user = new this.userModel({ name, email, password: hashed, provider: 'local' });
    await user.save();

    user.dbName = `sociantra_user_${user._id}`;
    await user.save();

    await this.tenantConnectionService.getConnection(user.dbName);

    return this.generateTokens(user);
  }

  async login(email: string, password: string) {
    const user = await this.userModel.findOne({ email }).select('+password');
    console.log(user)
    if (!user || !user.password || !(await bcrypt.compare(password, user.password))) {
      throw new UnauthorizedException('Invalid credentials');
    }
    return this.generateTokens(user);
  }

  async googleLogin(profile: any) {
    const { id, displayName, emails, photos } = profile;
    let user = await this.userModel.findOne({ email: emails[0].value });

    if (!user) {
      user = new this.userModel({
        name: displayName,
        email: emails[0].value,
        googleId: id,
        profileImage: photos[0]?.value,
        provider: 'google',
      });
      await user.save();
    }

    if (!user.dbName) {
      user.dbName = `sociantra_user_${user._id}`;
      await user.save();
      await this.tenantConnectionService.getConnection(user.dbName);
    }

    return this.generateTokens(user);
  }

  private async generateTokens(user: User) {
    const payload = { sub: user._id, email: user.email, name: user.name, dbName: user.dbName };
    const accessToken = this.jwtService.sign(payload);
    return { accessToken, user };
  }
}