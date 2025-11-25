import { Module } from '@nestjs/common';
import { TenantConnectionService } from './tenant-connection.service';

@Module({
  providers: [TenantConnectionService],
  exports: [TenantConnectionService], // 👈 Export so other modules can use it
})
export class TenantModule {}
