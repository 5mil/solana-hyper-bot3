"""
Real-time GUI dashboard for Solana Hyper-Accumulation Bot.

Displays bot status, trading activity, performance metrics in a readable interface.
Features:
- Real-time status updates
- Trade history with P&L
- Performance charts
- Toggleable display modes (compact/detailed)
- Dark/light theme toggle
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from typing import Dict, Any, Optional, List
import threading
import queue
import json
from pathlib import Path


class BotGUI:
    """
    Real-time GUI dashboard for bot monitoring.
    
    Features:
    - Live status display
    - Trade log with scrolling history
    - Performance metrics (P&L, win rate, drawdown)
    - Toggleable compact/detailed view
    - Theme switcher (dark/light)
    """
    
    def __init__(self, title: str = "Solana Hyper-Bot v3.0"):
        """Initialize GUI."""
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("900x700")
        
        # State
        self.is_running = False
        self.theme = "dark"  # "dark" or "light"
        self.view_mode = "detailed"  # "compact" or "detailed"
        self.update_queue = queue.Queue()
        
        # Metrics tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.current_balance = 100.0
        self.peak_balance = 100.0
        self.cycle_count = 0
        self.blocked_count = 0
        
        # Create UI
        self._create_widgets()
        self._apply_theme()
        
        # Start update loop
        self._schedule_updates()
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Header with controls
        self._create_header(main_frame)
        
        # Status panel
        self._create_status_panel(main_frame)
        
        # Metrics panel
        self._create_metrics_panel(main_frame)
        
        # Trade log
        self._create_trade_log(main_frame)
        
        # Footer
        self._create_footer(main_frame)
    
    def _create_header(self, parent):
        """Create header with title and control buttons."""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Title
        title_label = ttk.Label(
            header_frame,
            text="🤖 Solana Hyper-Accumulation Bot",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Control buttons frame
        controls_frame = ttk.Frame(header_frame)
        controls_frame.grid(row=0, column=1, sticky=tk.E)
        
        # Theme toggle button
        self.theme_btn = ttk.Button(
            controls_frame,
            text="🌙 Dark",
            command=self._toggle_theme,
            width=10
        )
        self.theme_btn.grid(row=0, column=0, padx=5)
        
        # View mode toggle button
        self.view_btn = ttk.Button(
            controls_frame,
            text="📊 Detailed",
            command=self._toggle_view,
            width=12
        )
        self.view_btn.grid(row=0, column=1, padx=5)
        
        # Minimize/maximize button
        self.compact_btn = ttk.Button(
            controls_frame,
            text="⬇️ Compact",
            command=self._toggle_compact,
            width=12
        )
        self.compact_btn.grid(row=0, column=2, padx=5)
        
        header_frame.columnconfigure(1, weight=1)
    
    def _create_status_panel(self, parent):
        """Create status panel showing bot state."""
        status_frame = ttk.LabelFrame(parent, text="📡 Status", padding="10")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status indicator
        status_container = ttk.Frame(status_frame)
        status_container.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(status_container, text="Bot Status:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        self.status_label = ttk.Label(status_container, text="IDLE", font=("Arial", 10))
        self.status_label.grid(row=0, column=1, padx=10, sticky=tk.W)
        
        # Current cycle
        ttk.Label(status_container, text="Cycle:", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=(20, 0), sticky=tk.W)
        self.cycle_label = ttk.Label(status_container, text="0", font=("Arial", 10))
        self.cycle_label.grid(row=0, column=3, padx=10, sticky=tk.W)
        
        # Last update time
        ttk.Label(status_container, text="Last Update:", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=(20, 0), sticky=tk.W)
        self.time_label = ttk.Label(status_container, text="--:--:--", font=("Arial", 10))
        self.time_label.grid(row=0, column=5, padx=10, sticky=tk.W)
        
        # Current price (only shown in detailed mode)
        self.price_container = ttk.Frame(status_frame)
        self.price_container.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        ttk.Label(self.price_container, text="SOL Price:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        self.price_label = ttk.Label(self.price_container, text="$0.00", font=("Arial", 10))
        self.price_label.grid(row=0, column=1, padx=10, sticky=tk.W)
        
        ttk.Label(self.price_container, text="Regime:", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=(20, 0), sticky=tk.W)
        self.regime_label = ttk.Label(self.price_container, text="--", font=("Arial", 10))
        self.regime_label.grid(row=0, column=3, padx=10, sticky=tk.W)
    
    def _create_metrics_panel(self, parent):
        """Create metrics panel showing performance."""
        self.metrics_frame = ttk.LabelFrame(parent, text="📈 Performance Metrics", padding="10")
        self.metrics_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Create 3 columns for metrics
        # Column 1: Balance metrics
        col1 = ttk.Frame(self.metrics_frame)
        col1.grid(row=0, column=0, sticky=(tk.N, tk.W), padx=(0, 20))
        
        self._create_metric_row(col1, 0, "Current Balance:", "balance")
        self._create_metric_row(col1, 1, "Total P&L:", "pnl")
        self._create_metric_row(col1, 2, "Return %:", "return_pct")
        
        # Column 2: Trade metrics
        col2 = ttk.Frame(self.metrics_frame)
        col2.grid(row=0, column=1, sticky=(tk.N, tk.W), padx=(0, 20))
        
        self._create_metric_row(col2, 0, "Total Trades:", "trades")
        self._create_metric_row(col2, 1, "Win Rate:", "win_rate")
        self._create_metric_row(col2, 2, "Blocked:", "blocked")
        
        # Column 3: Risk metrics
        col3 = ttk.Frame(self.metrics_frame)
        col3.grid(row=0, column=2, sticky=(tk.N, tk.W))
        
        self._create_metric_row(col3, 0, "Peak Balance:", "peak")
        self._create_metric_row(col3, 1, "Drawdown:", "drawdown")
        self._create_metric_row(col3, 2, "Approval Rate:", "approval")
    
    def _create_metric_row(self, parent, row, label_text, metric_key):
        """Create a metric row with label and value."""
        ttk.Label(parent, text=label_text, font=("Arial", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=2)
        label = ttk.Label(parent, text="--", font=("Arial", 9))
        label.grid(row=row, column=1, sticky=tk.W, padx=10, pady=2)
        setattr(self, f"{metric_key}_metric", label)
    
    def _create_trade_log(self, parent):
        """Create scrolling trade log."""
        self.log_frame = ttk.LabelFrame(parent, text="📝 Trade Log", padding="10")
        self.log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create scrolled text widget
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            wrap=tk.WORD,
            width=100,
            height=15,
            font=("Consolas", 9)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.log_frame.rowconfigure(0, weight=1)
        self.log_frame.columnconfigure(0, weight=1)
        
        parent.rowconfigure(3, weight=1)
    
    def _create_footer(self, parent):
        """Create footer with additional info."""
        footer_frame = ttk.Frame(parent)
        footer_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.footer_label = ttk.Label(
            footer_frame,
            text="Ready to start trading simulation",
            font=("Arial", 8),
            foreground="gray"
        )
        self.footer_label.grid(row=0, column=0, sticky=tk.W)
    
    def _toggle_theme(self):
        """Toggle between dark and light themes."""
        self.theme = "light" if self.theme == "dark" else "dark"
        self._apply_theme()
        self.theme_btn.config(text="☀️ Light" if self.theme == "dark" else "🌙 Dark")
    
    def _toggle_view(self):
        """Toggle between compact and detailed view."""
        self.view_mode = "compact" if self.view_mode == "detailed" else "detailed"
        
        if self.view_mode == "compact":
            self.price_container.grid_remove()
            self.view_btn.config(text="📊 Compact")
        else:
            self.price_container.grid()
            self.view_btn.config(text="📊 Detailed")
    
    def _toggle_compact(self):
        """Toggle window size between compact and full."""
        current_height = self.root.winfo_height()
        if current_height > 400:
            self.root.geometry("900x350")
            self.compact_btn.config(text="⬆️ Expand")
        else:
            self.root.geometry("900x700")
            self.compact_btn.config(text="⬇️ Compact")
    
    def _apply_theme(self):
        """Apply color theme to GUI."""
        if self.theme == "dark":
            bg = "#1e1e1e"
            fg = "#ffffff"
            log_bg = "#2d2d2d"
            log_fg = "#e0e0e0"
        else:
            bg = "#ffffff"
            fg = "#000000"
            log_bg = "#f5f5f5"
            log_fg = "#000000"
        
        # Apply to root
        self.root.configure(bg=bg)
        
        # Apply to log
        self.log_text.configure(bg=log_bg, fg=log_fg)
    
    def _schedule_updates(self):
        """Schedule periodic GUI updates."""
        self._process_update_queue()
        self.root.after(100, self._schedule_updates)  # Update every 100ms
    
    def _process_update_queue(self):
        """Process all pending updates from queue."""
        while not self.update_queue.empty():
            try:
                update = self.update_queue.get_nowait()
                self._apply_update(update)
            except queue.Empty:
                break
    
    def _apply_update(self, update: Dict[str, Any]):
        """Apply an update to the GUI."""
        update_type = update.get("type")
        
        if update_type == "status":
            self._update_status(update)
        elif update_type == "trade":
            self._update_trade(update)
        elif update_type == "metrics":
            self._update_metrics(update)
        elif update_type == "log":
            self._append_log(update.get("message", ""))
    
    def _update_status(self, data: Dict[str, Any]):
        """Update status panel."""
        self.status_label.config(text=data.get("status", "IDLE"))
        self.cycle_label.config(text=str(data.get("cycle", 0)))
        self.time_label.config(text=datetime.now().strftime("%H:%M:%S"))
        
        if "price" in data:
            self.price_label.config(text=f"${data['price']:.2f}")
        if "regime" in data:
            self.regime_label.config(text=data["regime"])
    
    def _update_trade(self, data: Dict[str, Any]):
        """Update on new trade."""
        self.total_trades += 1
        
        pnl = data.get("pnl", 0)
        if pnl > 0:
            self.winning_trades += 1
        
        self.total_pnl += pnl
        self.current_balance = data.get("balance", self.current_balance)
        self.peak_balance = max(self.peak_balance, self.current_balance)
        
        # Log trade
        action = data.get("action", "UNKNOWN")
        size = data.get("size", 0)
        price = data.get("price", 0)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {action} {size:.4f} SOL @ ${price:.2f} | P&L: ${pnl:+.2f} | Balance: ${self.current_balance:.2f}\n"
        self._append_log(log_msg)
        
        self._update_metrics_display()
    
    def _update_metrics(self, data: Dict[str, Any]):
        """Update metrics from external data."""
        if "balance" in data:
            self.current_balance = data["balance"]
        if "pnl" in data:
            self.total_pnl = data["pnl"]
        if "trades" in data:
            self.total_trades = data["trades"]
        if "winning_trades" in data:
            self.winning_trades = data["winning_trades"]
        if "blocked" in data:
            self.blocked_count = data["blocked"]
        if "cycles" in data:
            self.cycle_count = data["cycles"]
        
        self._update_metrics_display()
    
    def _update_metrics_display(self):
        """Update all metric labels."""
        self.balance_metric.config(text=f"${self.current_balance:.2f}")
        self.pnl_metric.config(text=f"${self.total_pnl:+.2f}")
        
        return_pct = ((self.current_balance - 100.0) / 100.0) * 100
        self.return_pct_metric.config(text=f"{return_pct:+.2f}%")
        
        self.trades_metric.config(text=str(self.total_trades))
        
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        self.win_rate_metric.config(text=f"{win_rate:.1f}%")
        
        self.blocked_metric.config(text=str(self.blocked_count))
        
        self.peak_metric.config(text=f"${self.peak_balance:.2f}")
        
        drawdown = ((self.peak_balance - self.current_balance) / self.peak_balance * 100) if self.peak_balance > 0 else 0
        self.drawdown_metric.config(text=f"{drawdown:.2f}%")
        
        total_cycles = self.cycle_count
        approval_rate = ((total_cycles - self.blocked_count) / total_cycles * 100) if total_cycles > 0 else 0
        self.approval_metric.config(text=f"{approval_rate:.1f}%")
    
    def _append_log(self, message: str):
        """Append message to trade log."""
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        
        # Limit log size (keep last 1000 lines)
        lines = int(self.log_text.index('end-1c').split('.')[0])
        if lines > 1000:
            # Delete first 100 lines when limit exceeded
            self.log_text.delete('1.0', '101.0')
    
    def update(self, update_type: str, data: Dict[str, Any]):
        """
        Thread-safe update method.
        
        Args:
            update_type: Type of update ("status", "trade", "metrics", "log")
            data: Update data
        """
        update_dict = {"type": update_type, **data}
        self.update_queue.put(update_dict)
    
    def run(self):
        """Start GUI main loop (blocking)."""
        self.root.mainloop()
    
    def start_in_thread(self):
        """Start GUI in a separate thread (non-blocking)."""
        gui_thread = threading.Thread(target=self.run, daemon=True)
        gui_thread.start()
        return gui_thread
    
    def close(self):
        """Close the GUI."""
        self.root.quit()
        self.root.destroy()


# Standalone test
if __name__ == "__main__":
    import random
    import time
    
    gui = BotGUI()
    
    # Simulate updates
    def simulate_trading():
        """Simulate trading activity for testing."""
        time.sleep(1)
        
        for i in range(100):
            # Update status
            gui.update("status", {
                "status": "RUNNING",
                "cycle": i + 1,
                "price": 100 + random.uniform(-10, 10),
                "regime": random.choice(["TRENDING_UP", "TRENDING_DOWN", "RANGING"])
            })
            
            # Random trade
            if random.random() > 0.3:
                gui.update("trade", {
                    "action": random.choice(["BUY", "SELL"]),
                    "size": random.uniform(0.1, 1.0),
                    "price": 100 + random.uniform(-10, 10),
                    "pnl": random.uniform(-5, 10),
                    "balance": 100 + random.uniform(-20, 50)
                })
            
            time.sleep(2)
    
    # Start simulation in background
    sim_thread = threading.Thread(target=simulate_trading, daemon=True)
    sim_thread.start()
    
    # Run GUI
    gui.run()
