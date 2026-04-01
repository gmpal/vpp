# Missing Features & Questions for a Real Energy Community

## Additional Logical Questions

### Energy sharing & fairness
- If household A overproduces and household B under-produces, how is the surplus allocated?
- Is the cost/benefit split fair across members with different asset sizes?
- Can a household without solar panels still benefit from the community?

### Grid interaction realism
- Are grid export limits enforced per connection point?
- Do tariffs reflect real time-of-use pricing (peak/off-peak/shoulder)?
- Is there a feed-in tariff cap beyond which selling becomes unprofitable?

### Device diversity
- What happens when a household has a home battery (not an EV)?
- How do heat pumps or flexible loads participate in optimization?
- Can controllable loads be shifted in time (demand response)?

### Failure & edge cases
- If a solar inverter goes offline, does the system detect and adjust?
- What happens during a grid outage — can the community island?
- If forecasts are wildly wrong, does optimization still produce safe schedules?

---

## Missing Features (by priority)

### High — Core for any real community

| Feature | Why it matters |
|---------|---------------|
| **Peer-to-peer energy trading / sharing rules** | The system calculates net production but has no mechanism to allocate surplus between households. This is the core value proposition of an energy community. |
| **Stationary battery storage** | `battery.py` was deleted. EVs are the only storage. Real communities have home batteries (Tesla Powerwall, etc.) that are always available, unlike EVs that drive away. |
| **Real tariff structures** | Market data is synthetic with no TOU pricing, demand charges, or feed-in tariffs. Optimization can't save money if it doesn't know the price structure. |
| **Cost tracking & billing** | No per-household cost/savings calculation. Members need to see "you saved X this month" to stay engaged. |
| **Wind source completion** | Wind sources exist in the schema but `create_new_source` only fully works for solar (Kafka producer + pvlib). Wind uses windpowerlib but seems incomplete in the streaming path. |

### Medium — Needed for serious use

| Feature | Why it matters |
|---------|---------------|
| **Demand response / flexible loads** | Only generation and storage are optimized. Shifting dishwashers, water heaters, or EV charging to off-peak is often the biggest savings lever. |
| **Grid export limits** | Most real grid connections have a max export capacity. The optimizer doesn't constrain this. |
| **Alerts & notifications** | No way to tell a user "your production dropped 50%" or "grid prices are spiking, discharge your battery." |
| **Historical analytics / reports** | Community summary is a snapshot. No weekly/monthly trends, no savings reports, no comparison between forecast and actual. |
| **Real weather integration** | Weather endpoint falls back to synthetic data. Production forecasts should use actual weather forecasts (cloud cover, irradiance). |

### Lower — Differentiators

| Feature | Why it matters |
|---------|---------------|
| **Smart meter / inverter integration** | Currently all data is synthetic. A real deployment needs MQTT/Modbus/SunSpec connectors. |
| **Community governance** | Voting on rules, joining/leaving, minimum participation requirements. |
| **Regulatory reporting** | Energy communities in the EU have reporting obligations (RED II). |
| **Mobile-friendly UI** | Community members check their energy on phones, not desktops. |
| **Multi-community support** | One deployment serving multiple communities with data isolation. |

### Architectural gaps

- **No event-driven actions** — optimization runs on-demand, not triggered by price signals or forecast updates
- **No scheduling** — training/inference are manual `docker-compose` tasks, not cron-driven
- **Single-user optimization** — the optimizer treats all EVs as one aggregator; it should produce per-household schedules
- **No rollback on bad forecasts** — if inference produces garbage, there's no fallback to naive forecasts

---

## Summary

The biggest single gap is **energy sharing/trading between households** — without it, each household is just independently monitored. The "community" in energy community means collective benefit, and the system doesn't model that yet.
