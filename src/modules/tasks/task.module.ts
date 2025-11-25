import { Module } from '@nestjs/common';
import { TasksController } from './tasks.controller';
import { TasksService } from './tasks.service';
import { TenantConnectionService } from '../tenant/tenant-connection.service';



@Module({
  imports: [

  ],
controllers: [TasksController],
providers: [TasksService, TenantConnectionService],
})
export class TasksModule {}