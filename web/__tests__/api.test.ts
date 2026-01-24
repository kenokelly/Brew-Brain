/**
 * API Client Tests
 */

import { api, apiFetch, ApiClientError } from '../lib/api';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('apiFetch', () => {
    beforeEach(() => {
        mockFetch.mockClear();
    });

    it('should return data on successful response', async () => {
        const mockData = { status: 'success', data: { temp: 20 } };
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(mockData),
        });

        const result = await apiFetch('/api/status');
        expect(result).toEqual(mockData);
    });

    it('should throw ApiClientError on non-OK response', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: false,
            status: 404,
            json: () => Promise.resolve({ error: 'Not found' }),
        });

        await expect(apiFetch('/api/missing')).rejects.toThrow(ApiClientError);
    });

    it('should throw ApiClientError on API-level error', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ error: 'Invalid input' }),
        });

        await expect(apiFetch('/api/test')).rejects.toThrow('Invalid input');
    });
});

describe('api convenience methods', () => {
    beforeEach(() => {
        mockFetch.mockClear();
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ success: true }),
        });
    });

    it('api.get should call fetch with GET method', async () => {
        await api.get('/api/status');
        expect(mockFetch).toHaveBeenCalledWith('/api/status', expect.objectContaining({ method: 'GET' }));
    });

    it('api.post should call fetch with POST method and body', async () => {
        await api.post('/api/test', { data: 'value' });
        expect(mockFetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({ data: 'value' }),
        }));
    });
});
