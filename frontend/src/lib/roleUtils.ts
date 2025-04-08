import { User } from './api';

// 角色常量定义（与后端保持一致）
export const ROLE_USER = 0;         // 普通用户
export const ROLE_ADMIN = 1;        // 管理员
export const ROLE_AGENT = 2;        // 一级代理
export const ROLE_SENIOR_AGENT = 3; // 高级代理

/**
 * 检查用户是否为管理员
 */
export function isAdmin(user?: User | null): boolean {
  if (!user) return false;
  return user.is_admin || user.role === ROLE_ADMIN;
}

/**
 * 检查用户是否为代理（包括一级代理和高级代理）
 */
export function isAgent(user?: User | null): boolean {
  if (!user) return false;
  return user.role === ROLE_AGENT || user.role === ROLE_SENIOR_AGENT;
}

/**
 * 检查用户是否为高级代理
 */
export function isSeniorAgent(user?: User | null): boolean {
  if (!user) return false;
  return user.role === ROLE_SENIOR_AGENT;
}

/**
 * 检查用户是否有管理员权限（管理员或高级代理）
 */
export function hasAdminAccess(user?: User | null): boolean {
  if (!user) return false;
  return isAdmin(user) || isSeniorAgent(user);
}

/**
 * 检查用户是否有任何特殊权限（管理员或任何级别的代理）
 */
export function hasSpecialRole(user?: User | null): boolean {
  if (!user) return false;
  return user.role > ROLE_USER;
}

/**
 * 获取用户角色名称
 */
export function getRoleName(role: number): string {
  switch (role) {
    case ROLE_ADMIN:
      return '管理员';
    case ROLE_AGENT:
      return '一级代理';
    case ROLE_SENIOR_AGENT:
      return '高级代理';
    case ROLE_USER:
    default:
      return '普通用户';
  }
} 