// 今日（2026-04-22）新增：昵称校验服务
import sensitiveWords from './sensitive-words.json';
export async function validateNickname(name: string): Promise<{ok: boolean; reason?: string}> {
  if (name.length < 2 || name.length > 20) return {ok: false, reason: 'length'};
  for (const w of sensitiveWords) if (name.includes(w)) return {ok: false, reason: 'sensitive'};
  return {ok: true};
}
