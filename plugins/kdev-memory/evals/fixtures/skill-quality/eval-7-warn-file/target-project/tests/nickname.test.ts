import { validateNickname } from '../src/services/nickname-validator';
test('rejects too short', async () => expect((await validateNickname('a')).ok).toBe(false));
