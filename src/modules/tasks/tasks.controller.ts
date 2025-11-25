import { Controller, Get, Post, Put, Delete, Body, Param, Req, UseGuards } from '@nestjs/common';
import { TasksService } from './tasks.service';
import { JwtAuthGuard } from '../auth/guards/jwt.guard';
import { CreateTaskDto } from './dto/create-task.dto';
import { UpdateTaskDto } from './dto/update-task.dto';
import { ApiBearerAuth } from '@nestjs/swagger';
import { AuthGuard } from '@nestjs/passport';
import { TenantGuard } from '../tenant/tenant.guard';

 @ApiBearerAuth('access-token')
@Controller('tasks')
@UseGuards(JwtAuthGuard, TenantGuard)
export class TasksController {
constructor(private readonly tasksService: TasksService) {}


@Post()
createTask(@Req() req, @Body() body: CreateTaskDto) {
  const userId = req.user.userId;
  const dbName = req.user.dbName;
  return this.tasksService.createTask(userId,dbName, body);
}

@Put(':id')
updateTask(@Req() req, @Param('id') id: string, @Body() body: UpdateTaskDto) {
  const userId = req.user.userId;
  return this.tasksService.updateTask(userId, id, body);
}



@Get()
async getTasks(@Req() req) {
const userId = req.user.userId;
return this.tasksService.getAllTasks(userId);
}


@Get(':id')
async getTask(@Req() req, @Param('id') id: string) {
const userId = req.user.userId;
return this.tasksService.getTaskById(userId, id);
}





@Delete(':id')
async deleteTask(@Req() req, @Param('id') id: string) {
const userId = req.user.userId;
return this.tasksService.deleteTask(userId, id);
}
}