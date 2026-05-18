/**
 * Settings Page Tests
 * Stream 5.1 — Frontend QA
 * 
 * Tests the Settings page fetches config from /api/settings
 * and sends PATCH requests on save.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// Mock SWR to return controlled data
const mockMutate = vi.fn();
vi.mock('swr', () => ({
  default: () => ({
    data: {
      data: {
        bf_user: 'test_user',
        bf_key: '********',
        batch_name: 'Test IPA',
        og: 1.055,
        target_fg: 1.010,
        alert_telegram_token: '',
        alert_telegram_chat: '',
        serp_api_key: '',
      }
    },
    error: null,
    isLoading: false,
    mutate: mockMutate,
  }),
}));

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}));

// Must import after mocks
import Settings from '@/app/settings/page';

describe('Settings Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the settings heading', () => {
    render(<Settings />);
    expect(screen.getByText('System Configuration')).toBeInTheDocument();
  });

  it('renders the API Integrations section', () => {
    render(<Settings />);
    expect(screen.getByText('API Integrations')).toBeInTheDocument();
  });

  it('renders Brewfather User ID input with value from SWR', () => {
    render(<Settings />);
    const input = screen.getByDisplayValue('test_user');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('name', 'bf_user');
  });

  it('renders the save button', () => {
    render(<Settings />);
    expect(screen.getByText('Save Changes')).toBeInTheDocument();
  });

  it('sends PATCH request on save', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ status: 'updated' }),
    });
    global.fetch = mockFetch as any;

    render(<Settings />);
    
    // Change a field
    const input = screen.getByDisplayValue('test_user');
    fireEvent.change(input, { target: { value: 'new_user', name: 'bf_user' } });
    
    // Click save
    const saveButton = screen.getByText('Save Changes');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/settings', expect.objectContaining({
        method: 'PATCH',
      }));
    });
  });
});
