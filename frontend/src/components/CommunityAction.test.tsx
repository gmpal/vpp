import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import CommunityAction from './CommunityAction';
import * as api from '../api';

jest.mock('../api');
const mockApi = api as jest.Mocked<typeof api>;

const baseSummary = {
  total_production: 5.0,
  total_consumption: 3.0,
  net: 2.0,
  ev_soc_total: 0,
  ev_soc_capacity: 0,
  action: 'selling' as const,
  household_count: 1,
  ev_count: 0,
};

describe('CommunityAction', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.clearAllTimers();
  });

  it('renders nothing while loading (summary is null)', () => {
    mockApi.getCommunitySummary.mockImplementation(() => new Promise(() => {}));
    const { container } = render(<CommunityAction />);
    expect(container.firstChild).toBeNull();
  });

  it('renders Selling state correctly', async () => {
    mockApi.getCommunitySummary.mockResolvedValue({ ...baseSummary, action: 'selling', net: 2.3 });
    render(<CommunityAction />);
    await waitFor(() => expect(screen.getByText(/Selling/i)).toBeInTheDocument());
    expect(screen.getByText(/2\.30 kW to the grid/i)).toBeInTheDocument();
  });

  it('renders Buying state correctly', async () => {
    mockApi.getCommunitySummary.mockResolvedValue({
      ...baseSummary, action: 'buying', net: -1.1,
    });
    render(<CommunityAction />);
    await waitFor(() => expect(screen.getByText(/Buying/i)).toBeInTheDocument());
    expect(screen.getByText(/consider charging your EVs/i)).toBeInTheDocument();
  });

  it('renders Charging EVs state correctly', async () => {
    mockApi.getCommunitySummary.mockResolvedValue({
      ...baseSummary, action: 'charging_evs', net: 1.0, ev_count: 2,
    });
    render(<CommunityAction />);
    await waitFor(() => expect(screen.getByText(/Charging EVs/i)).toBeInTheDocument());
    expect(screen.getByText(/surplus/i)).toBeInTheDocument();
  });

  it('renders Self-sufficient state correctly', async () => {
    mockApi.getCommunitySummary.mockResolvedValue({
      ...baseSummary, action: 'self_sufficient', net: 0,
    });
    render(<CommunityAction />);
    await waitFor(() => expect(screen.getByText(/Self-sufficient/i)).toBeInTheDocument());
    expect(screen.getByText(/production matches consumption/i)).toBeInTheDocument();
  });

  it('shows Currently label', async () => {
    mockApi.getCommunitySummary.mockResolvedValue(baseSummary);
    render(<CommunityAction />);
    await waitFor(() => expect(screen.getByText(/Currently/i)).toBeInTheDocument());
  });

  it('polls getCommunitySummary on interval', async () => {
    jest.useFakeTimers();
    mockApi.getCommunitySummary.mockResolvedValue(baseSummary);
    render(<CommunityAction />);
    await waitFor(() => expect(mockApi.getCommunitySummary).toHaveBeenCalledTimes(1));
    jest.advanceTimersByTime(5000);
    await waitFor(() => expect(mockApi.getCommunitySummary).toHaveBeenCalledTimes(2));
    jest.useRealTimers();
  });
});
