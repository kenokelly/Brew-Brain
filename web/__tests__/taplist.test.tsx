/**
 * Tap List Page Tests
 * Stream 5.1 — Frontend QA
 * 
 * Tests the Tap List page renders tap cards,
 * shows ABV/volume data, and handles empty state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

const MOCK_TAP_DATA = {
  data: {
    taps: [
      {
        tap_id: 'tap1',
        beer_name: 'Hop Storm IPA',
        style: 'American IPA',
        abv: 6.8,
        keg_volume_l: 19,
        remaining_pct: 75,
        qr_code_base64: 'dGVzdA==', // base64("test")
      },
      {
        tap_id: 'tap2',
        beer_name: 'Midnight Stout',
        style: 'Imperial Stout',
        abv: 8.2,
        keg_volume_l: 19,
        remaining_pct: 12,
        qr_code_base64: 'dGVzdA==',
      },
    ],
  },
};

// Mock SWR
vi.mock('swr', () => ({
  default: vi.fn(() => ({
    data: MOCK_TAP_DATA,
    error: null,
    isLoading: false,
  })),
}));

// Mock framer-motion to avoid animation complexity in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

import TapList from '@/app/taplist/page';

describe('Tap List Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page heading', () => {
    render(<TapList />);
    expect(screen.getByText('On Tap')).toBeInTheDocument();
  });

  it('renders both tap cards', () => {
    render(<TapList />);
    expect(screen.getByText('Hop Storm IPA')).toBeInTheDocument();
    expect(screen.getByText('Midnight Stout')).toBeInTheDocument();
  });

  it('displays correct ABV values', () => {
    render(<TapList />);
    expect(screen.getByText(/6\.8% ABV/)).toBeInTheDocument();
    expect(screen.getByText(/8\.2% ABV/)).toBeInTheDocument();
  });

  it('displays correct styles', () => {
    render(<TapList />);
    expect(screen.getByText('American IPA')).toBeInTheDocument();
    expect(screen.getByText('Imperial Stout')).toBeInTheDocument();
  });

  it('displays remaining percentages', () => {
    render(<TapList />);
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('12%')).toBeInTheDocument();
  });

  it('displays keg sizes', () => {
    render(<TapList />);
    const kegLabels = screen.getAllByText(/Keg size: 19L/);
    expect(kegLabels).toHaveLength(2);
  });

  it('renders QR code images when available', () => {
    render(<TapList />);
    const qrImages = screen.getAllByAltText('QR Code');
    expect(qrImages).toHaveLength(2);
    expect(qrImages[0]).toHaveAttribute('src', expect.stringContaining('data:image/png;base64'));
  });
});

describe('Tap List Empty State', () => {
  it('renders empty grid when no taps configured', () => {
    // Override mock for this specific test
    const useSWR = vi.mocked(await import('swr')).default;
    (useSWR as any).mockReturnValueOnce({
      data: { data: { taps: [] } },
      error: null,
      isLoading: false,
    });

    render(<TapList />);
    expect(screen.getByText('On Tap')).toBeInTheDocument();
  });
});
