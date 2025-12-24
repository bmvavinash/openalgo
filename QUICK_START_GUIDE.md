# Quick Start Guide - Strategy Performance Management

## 🚀 Quick Setup (5 Minutes)

### Step 1: Run Initial Analysis

```bash
python daily_strategy_analyzer.py
```

This analyzes today's strategies and creates initial categories.

### Step 2: Access Dashboard

Open browser: `http://localhost:5000/strategy-performance/`

### Step 3: Set Preferences

1. Check "Top Performance" (or your preferred categories)
2. Click "Save Preferences"
3. Done!

## 📋 Daily Workflow

### Automatic (Recommended)
- **Nothing to do!** System runs automatically at 3:35 PM IST
- Categories update daily
- Restrictions auto-adjust

### Manual (If Needed)
- Go to dashboard
- Click "Run Daily Analysis Now"
- Wait for completion
- Refresh page

## 🎯 Common Tasks

### Task 1: Start Only Top Performers

1. Dashboard → Check "Top Performance" → Save
2. Try starting strategies
3. Only top performers will start

### Task 2: Restrict Strategy to SELL Only

1. Dashboard → Find strategy → "Edit Restrictions"
2. Enter: "SELL"
3. Strategy will only execute SELL orders

### Task 3: View Current Categories

1. Dashboard → See all strategies grouped by category
2. Each shows: P&L, Allowed Actions, Restrictions

## ⚙️ Configuration

### Change Performance Thresholds

Edit `config/strategy_performance.json`:

```json
{
  "performance_thresholds": {
    "top_performance": 200.0,    // Change to 200
    "average_performance": 50.0,  // Change to 50
    "low_performance": -50.0       // Change to -50
  }
}
```

### Manual Restrictions

**Via Dashboard:**
- Click "Edit Restrictions" on any strategy
- Enter actions: "BUY", "SELL", or "BUY, SELL"

**Via API:**
```bash
curl -X POST http://localhost:5000/strategy-performance/restriction \
  -H "Content-Type: application/json" \
  -d '{"strategy_name": "Bear Put Spread", "allowed_actions": ["BUY"]}'
```

## 🔍 Troubleshooting

### Issue: No strategies in categories
**Solution:** Run daily analysis first:
```bash
python daily_strategy_analyzer.py
```

### Issue: Scheduler not running
**Solution:** Check if scheduler is started in `blueprints/strategy.py`
- Should see: "Daily analysis scheduler integrated" in logs

### Issue: Preferences not saving
**Solution:** Check browser console for errors
- Make sure you're logged in
- Check network tab for API errors

### Issue: Strategies not filtering
**Solution:** 
1. Check user preferences are set
2. Check strategy categories match preferences
3. Check logs for filter messages

## 📊 Understanding Categories

### Top Performance
- **Criteria**: Average P&L >= threshold (default: 100)
- **Use**: Start these strategies
- **Example**: Sell Strangle (Rs 705 avg P&L)

### Average Performance
- **Criteria**: 0 <= Average P&L < threshold
- **Use**: Start with caution
- **Example**: Iron Condor (Rs 24 avg P&L)

### Low Performance
- **Criteria**: Average P&L < 0
- **Use**: Avoid or restrict
- **Example**: Buy Strangle (Rs -705 avg P&L)

## 🎓 Best Practices

1. **Run Analysis Daily**: Let scheduler handle it automatically
2. **Review Categories**: Check dashboard weekly
3. **Adjust Thresholds**: Based on your risk tolerance
4. **Set Restrictions**: For consistently losing strategies
5. **Monitor Performance**: Track how categories change over time

## 📞 Support

- **Documentation**: See `STRATEGY_PERFORMANCE_SYSTEM.md`
- **API Docs**: See `INTEGRATION_COMPLETE.md`
- **Examples**: See `integrate_strategy_filter_example.py`

## ✅ Checklist

- [ ] Run initial analysis
- [ ] Access dashboard
- [ ] Set user preferences
- [ ] Verify scheduler is running
- [ ] Test starting a strategy
- [ ] Check categories update daily

## 🎉 You're Ready!

The system is now fully operational. Strategies will automatically:
- ✅ Respect your category preferences
- ✅ Follow buy/sell restrictions
- ✅ Update categories daily
- ✅ Prevent unprofitable actions

