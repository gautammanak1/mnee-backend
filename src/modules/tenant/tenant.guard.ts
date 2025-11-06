import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { TenantConnectionService } from './tenant-connection.service';

@Injectable()
export class TenantGuard implements CanActivate {
  constructor(private readonly tenantService: TenantConnectionService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const req = context.switchToHttp().getRequest();
    const user = req.user;

    if (!user || !user.dbName) {
      throw new UnauthorizedException('Missing tenant info. Invalid or missing JWT.');
    }

    await this.tenantService.getConnection(user.dbName);
    return true;
  }
}
