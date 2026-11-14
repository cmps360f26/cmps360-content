"""
================================================================================
Interactive Gradient Descent Animation in Python
Objective Function: f(x) = x^2  |  Analytical Gradient: df/dx = 2x
================================================================================

Educational Objectives:
-----------------------
1. Visually demonstrate how Gradient Descent iteratively moves from an initial
   point x_0 toward the global minimum at x* = 0, where f'(0) = 0.
2. Demystify the update rule:
       x_{t+1} = x_t - alpha * (2 * x_t)
3. Explore the critical role of the Learning Rate (alpha):
   - Small learning rate: slow convergence.
   - Appropriate learning rate: faster convergence.
   - Excessively large learning rate: overshooting or divergence.

Interactive Controls Provided:
------------------------------
- Sliders:
    * Learning Rate (alpha): 0.01 to 1.15
    * Initial Position (x_0): -6.0 to +6.0
    * Animation Speed: 50 ms to 800 ms per step
- Buttons:
    * [Pause / Resume]: Freeze or resume continuous execution.
    * [Step (+1)]: Advance exactly one gradient descent iteration manually.
    * [Restart]: Reset iteration counter, trajectory, and telemetry to current slider values.
    * Presets: One-click buttons to instantly load representative alpha regimes.

Setup & Execution Instructions:
-------------------------------
Prerequisites:
    Python 3.8+ with NumPy and Matplotlib installed:
        pip install numpy matplotlib

Run the script:
    python gradient_descent_anim.py
================================================================================
"""

import sys
import itertools
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button


class GradientDescentVisualizer:
    """
    Educational, interactive visualizer demonstrating gradient descent
    optimization on the 1D convex parabola f(x) = x^2.
    """

    def __init__(
        self,
        x0: float = 5.0,
        alpha: float = 0.15,
        max_iters: int = 100,
        tolerance: float = 1e-4,
        divergence_threshold: float = 25.0,
        interval_ms: int = 250,
    ):
        """
        Initialize the visualizer parameters, state, and interactive UI.

        Parameters
        ----------
        x0 : float
            Starting position on the x-axis (default: 5.0).
        alpha : float
            Initial learning rate (default: 0.15).
        max_iters : int
            Maximum iterations before stopping (default: 100).
        tolerance : float
            Threshold for gradient norm to declare convergence (default: 1e-4).
        divergence_threshold : float
            Absolute value of x beyond which optimization is deemed divergent.
        interval_ms : int
            Delay between animation frames in milliseconds (default: 250).
        """
        self.x0 = float(x0)
        self.alpha = float(alpha)
        self.max_iters = max_iters
        self.tolerance = tolerance
        self.divergence_threshold = divergence_threshold
        self.interval_ms = interval_ms

        # Optimization State Tracking
        self.x = self.x0
        self.iteration = 0
        self.history_x = [self.x0]
        self.history_y = [self.f(self.x0)]
        self.history_grad = [self.grad_f(self.x0)]

        # Execution Status Flags
        self.is_running = True
        self.is_converged = False
        self.is_diverged = False
        self.status_message = "Running..."
        self.status_color = "#38BDF8"  # Sky blue

        # Build UI and Figure
        self._setup_figure_and_widgets()
        self._init_plot_elements()
        self._update_telemetry()
        self._update_banner()

        # Connect Matplotlib Animation
        # Note: We maintain a SINGLE FuncAnimation instance to avoid timer leaks
        # when restarting or pausing/resuming.
        self.anim = FuncAnimation(
            self.fig,
            self._on_animation_frame,
            frames=itertools.count(),
            interval=self.interval_ms,
            blit=False,
            cache_frame_data=False,
        )

    # --------------------------------------------------------------------------
    # Mathematical Core Functions
    # --------------------------------------------------------------------------
    @staticmethod
    def f(x: float) -> float:
        """Objective function: f(x) = x^2."""
        return x ** 2

    @staticmethod
    def grad_f(x: float) -> float:
        """Analytical gradient (derivative): df/dx = 2x."""
        return 2.0 * x

    # --------------------------------------------------------------------------
    # GUI Layout and Interactive Widgets
    # --------------------------------------------------------------------------
    def _setup_figure_and_widgets(self):
        """Construct the figure, main plot axes, and widget controls."""
        # Figure canvas with a modern off-white background
        self.fig = plt.figure(figsize=(15.2, 9.2), facecolor="#F8FAFC")
        try:
            self.fig.canvas.manager.set_window_title(
                "Interactive Gradient Descent Animation: f(x) = x²"
            )
        except Exception:
            pass

        # 1. Main Parabola Axis (Left Panel - 54% width)
        self.ax_parabola = self.fig.add_axes(
            [0.06, 0.35, 0.54, 0.57], facecolor="#FFFFFF"
        )

        # 2. Loss vs. Iteration Axis (Top Right Panel)
        self.ax_loss = self.fig.add_axes(
            [0.67, 0.65, 0.29, 0.27], facecolor="#FFFFFF"
        )

        # 3. Real-time Telemetry & Metrics Card (Bottom Right Panel)
        self.ax_stats = self.fig.add_axes(
            [0.67, 0.34, 0.29, 0.27], facecolor="#0F172A"
        )
        self.ax_stats.set_xticks([])
        self.ax_stats.set_yticks([])
        for spine in self.ax_stats.spines.values():
            spine.set_color("#334155")
            spine.set_linewidth(1.5)

        # 4. Sliders Row (y = 0.26 to 0.29)
        self.ax_slider_alpha = self.fig.add_axes(
            [0.13, 0.26, 0.20, 0.026], facecolor="#E2E8F0"
        )
        self.ax_slider_x0 = self.fig.add_axes(
            [0.44, 0.26, 0.18, 0.026], facecolor="#E2E8F0"
        )
        self.ax_slider_speed = self.fig.add_axes(
            [0.74, 0.26, 0.18, 0.026], facecolor="#E2E8F0"
        )

        self.slider_alpha = Slider(
            self.ax_slider_alpha,
            "Learning Rate (α)",
            0.01,
            1.15,
            valinit=self.alpha,
            valstep=0.01,
            color="#2563EB",
        )
        self.slider_x0 = Slider(
            self.ax_slider_x0,
            "Initial (x₀)",
            -6.0,
            6.0,
            valinit=self.x0,
            valstep=0.25,
            color="#059669",
        )
        self.slider_speed = Slider(
            self.ax_slider_speed,
            "Speed (ms)",
            50,
            800,
            valinit=self.interval_ms,
            valstep=25,
            color="#7C3AED",
        )

        # Format slider labels
        for s in (self.slider_alpha, self.slider_x0, self.slider_speed):
            s.label.set_fontsize(9.2)
            s.label.set_fontweight("bold")
            s.label.set_color("#1E293B")
            s.valtext.set_fontsize(9.2)
            s.valtext.set_fontweight("bold")

        # 5. Buttons Row (y = 0.18 to 0.225)
        # Action controls
        self.ax_btn_pause = self.fig.add_axes([0.06, 0.18, 0.085, 0.045])
        self.ax_btn_step = self.fig.add_axes([0.155, 0.18, 0.080, 0.045])
        self.ax_btn_restart = self.fig.add_axes([0.245, 0.18, 0.095, 0.045])

        self.btn_pause = Button(
            self.ax_btn_pause,
            "Pause",
            color="#E2E8F0",
            hovercolor="#CBD5E1",
        )
        self.btn_step = Button(
            self.ax_btn_step,
            "Step (+1)",
            color="#E2E8F0",
            hovercolor="#CBD5E1",
        )
        self.btn_restart = Button(
            self.ax_btn_restart,
            "Restart",
            color="#DBEAFE",
            hovercolor="#BFDBFE",
        )

        for btn in (self.btn_pause, self.btn_step, self.btn_restart):
            btn.label.set_fontsize(9.2)
            btn.label.set_fontweight("bold")
            btn.label.set_color("#0F172A")

        # Educational Preset Buttons
        self.preset_configs = [
            ("Slow (0.03)", 0.03, "#F1F5F9", "#475569"),
            ("Optimal (0.15)", 0.15, "#DCFCE7", "#166534"),
            ("Fast (0.35)", 0.35, "#FEF9C3", "#854D0E"),
            ("1-Step (0.50)", 0.50, "#E0E7FF", "#3730A3"),
            ("Oscillate (0.85)", 0.85, "#FFEDD5", "#9A3412"),
            ("Diverge (1.05)", 1.05, "#FEE2E2", "#991B1B"),
        ]

        self.preset_buttons = []
        preset_start_x = 0.36
        preset_w = 0.095
        for i, (name, val, col, text_col) in enumerate(self.preset_configs):
            ax_p = self.fig.add_axes(
                [preset_start_x + i * (preset_w + 0.008), 0.18, preset_w, 0.045]
            )
            btn = Button(ax_p, name, color=col, hovercolor="#FFFFFF")
            btn.label.set_fontsize(8.5)
            btn.label.set_fontweight("bold")
            btn.label.set_color(text_col)
            self.preset_buttons.append((btn, val))

        # 6. Educational Regime Banner Axis (y = 0.02 to 0.14)
        self.ax_banner = self.fig.add_axes(
            [0.06, 0.02, 0.90, 0.13], facecolor="#F1F5F9"
        )
        self.ax_banner.set_xticks([])
        self.ax_banner.set_yticks([])
        for spine in self.ax_banner.spines.values():
            spine.set_color("#CBD5E1")
            spine.set_linewidth(1.2)

        # Attach Interactive Callbacks
        self.slider_alpha.on_changed(self._on_alpha_slider_changed)
        self.slider_x0.on_changed(self._on_x0_slider_changed)
        self.slider_speed.on_changed(self._on_speed_slider_changed)

        self.btn_pause.on_clicked(self._on_pause_clicked)
        self.btn_step.on_clicked(self._on_step_clicked)
        self.btn_restart.on_clicked(self._on_restart_clicked)

        for btn, val in self.preset_buttons:
            # Bind closure with default parameter to avoid late-binding bug
            btn.on_clicked(lambda event, v=val: self._on_preset_clicked(v))

    # --------------------------------------------------------------------------
    # Plot Artists Initialization
    # --------------------------------------------------------------------------
    def _init_plot_elements(self):
        """Initialize static curve lines, scatter markers, and text placeholders."""
        # --- Main Parabola Subplot ---
        self.curve_x = np.linspace(-7.0, 7.0, 600)
        self.curve_y = self.f(self.curve_x)

        # Parabola curve and fill
        self.ax_parabola.plot(
            self.curve_x,
            self.curve_y,
            color="#1E40AF",
            lw=2.8,
            label=r"$f(x) = x^2$",
            zorder=2,
        )
        self.ax_parabola.fill_between(
            self.curve_x,
            self.curve_y,
            color="#3B82F6",
            alpha=0.06,
            zorder=1,
        )

        # Global Minimum Marker at (0, 0)
        self.ax_parabola.scatter(
            [0],
            [0],
            color="#F59E0B",
            edgecolors="#78350F",
            s=220,
            marker="*",
            lw=1.8,
            zorder=6,
            label="Global Min (0, 0)",
        )
        self.ax_parabola.axvline(0, color="#CBD5E1", linestyle="--", lw=1.0, zorder=1)
        self.ax_parabola.axhline(0, color="#CBD5E1", linestyle="--", lw=1.0, zorder=1)

        # Trajectory Path Artist
        (self.line_trajectory,) = self.ax_parabola.plot(
            self.history_x,
            self.history_y,
            color="#64748B",
            linestyle="--",
            lw=1.6,
            marker="o",
            markersize=5,
            markerfacecolor="#94A3B8",
            zorder=3,
            label="Trajectory Steps",
        )

        # Tangent Line Artist: y - f(x_t) = 2x_t * (x - x_t)
        (self.line_tangent,) = self.ax_parabola.plot(
            [],
            [],
            color="#EA580C",
            linestyle="-",
            lw=2.2,
            zorder=4,
            label=r"Tangent: $\frac{df}{dx} = 2x$",
        )

        # Current Point Artists (Core Marker + Glowing Halo)
        self.scatter_halo = self.ax_parabola.scatter(
            [self.x],
            [self.f(self.x)],
            color="#EF4444",
            alpha=0.25,
            s=320,
            zorder=7,
        )
        self.scatter_current = self.ax_parabola.scatter(
            [self.x],
            [self.f(self.x)],
            color="#DC2626",
            edgecolors="#FFFFFF",
            s=140,
            lw=2.2,
            zorder=8,
            label=r"Current $(x_t, f(x_t))$",
        )

        # Coordinate Annotation attached to current point
        self.point_annot = self.ax_parabola.annotate(
            f"$x = {self.x:.3f}$\n$f(x) = {self.f(self.x):.3f}$",
            xy=(self.x, self.f(self.x)),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="#FEF2F2", ec="#DC2626", lw=1.2),
            fontsize=9.0,
            fontweight="bold",
            color="#991B1B",
            zorder=9,
        )

        # Dynamic Step Arrow Annotation
        self.step_arrow = self.ax_parabola.annotate(
            "",
            xy=(self.x, self.f(self.x)),
            xytext=(self.x, self.f(self.x)),
            arrowprops=dict(
                arrowstyle="->",
                color="#7C3AED",
                lw=2.0,
                mutation_scale=14,
            ),
            zorder=5,
        )

        # Format Main Parabola Axes
        self.ax_parabola.set_xlim(-6.5, 6.5)
        self.ax_parabola.set_ylim(-2, 42)
        self.ax_parabola.set_xlabel(
            r"Parameter Value $x$", fontsize=11, fontweight="bold", color="#1E293B"
        )
        self.ax_parabola.set_ylabel(
            r"Objective Cost $f(x) = x^2$",
            fontsize=11,
            fontweight="bold",
            color="#1E293B",
        )
        self.ax_parabola.set_title(
            r"Optimization Landscape: Minimizing $f(x) = x^2$ via Gradient Descent",
            fontsize=12.5,
            fontweight="bold",
            color="#0F172A",
            pad=10,
        )
        self.ax_parabola.grid(True, linestyle=":", alpha=0.55, color="#94A3B8")
        self.ax_parabola.legend(
            loc="upper center",
            fontsize=8.5,
            framealpha=0.92,
            ncol=4,
            facecolor="#FFFFFF",
            edgecolor="#CBD5E1",
        )

        # --- Loss History Subplot ---
        (self.line_loss,) = self.ax_loss.plot(
            [0],
            self.history_y,
            color="#059669",
            lw=2.0,
            marker="s",
            markersize=4.5,
            markerfacecolor="#10B981",
        )
        self.ax_loss.set_xlim(0, 15)
        self.ax_loss.set_ylim(0, max(26, self.f(self.x0) * 1.15))
        self.ax_loss.set_xlabel(
            "Iteration (t)", fontsize=9.5, fontweight="bold", color="#1E293B"
        )
        self.ax_loss.set_ylabel(
            r"Loss $f(x)$", fontsize=9.5, fontweight="bold", color="#1E293B"
        )
        self.ax_loss.set_title(
            r"Loss Curve: $f(x_t)$ vs. Iteration",
            fontsize=10.5,
            fontweight="bold",
            color="#0F172A",
            pad=6,
        )
        self.ax_loss.grid(True, linestyle=":", alpha=0.55, color="#94A3B8")

        # --- Stats & Telemetry Text (Dark Card) ---
        self.stats_text = self.ax_stats.text(
            0.04,
            0.95,
            "",
            transform=self.ax_stats.transAxes,
            fontsize=8.6,
            family="monospace",
            verticalalignment="top",
            color="#F8FAFC",
        )

        # --- Educational Banner Text ---
        self.banner_text = self.ax_banner.text(
            0.02,
            0.90,
            "",
            transform=self.ax_banner.transAxes,
            fontsize=9.2,
            verticalalignment="top",
            color="#0F172A",
            wrap=True,
        )

        self._update_tangent_line()

    # --------------------------------------------------------------------------
    # Optimization Step Execution
    # --------------------------------------------------------------------------
    def _perform_step(self):
        """
        Execute a single gradient descent update step:
            x_{t+1} = x_t - alpha * 2x_t
        """
        if self.is_converged or self.is_diverged:
            return

        grad = self.grad_f(self.x)
        step_val = -self.alpha * grad
        new_x = self.x + step_val
        prev_x = self.x

        self.iteration += 1
        self.x = new_x
        self.history_x.append(self.x)
        self.history_y.append(self.f(self.x))
        self.history_grad.append(self.grad_f(self.x))

        # Check for convergence: gradient magnitude below tolerance
        if abs(grad) < self.tolerance or abs(step_val) < 1e-7:
            self.is_converged = True
            self.is_running = False
            self.btn_pause.label.set_text("Resume")
            self.status_message = (
                f"CONVERGED in {self.iteration} steps! (|df/dx| < {self.tolerance:.1e})"
            )
            self.status_color = "#10B981"  # Emerald Green

        # Check for divergence: position exploded beyond threshold
        elif abs(self.x) > self.divergence_threshold or self.f(self.x) > 1500.0:
            self.is_diverged = True
            self.is_running = False
            self.btn_pause.label.set_text("Resume")
            self.status_message = (
                f"DIVERGED! |x| = {abs(self.x):.2f} > {self.divergence_threshold:.0f} (Exploding)"
            )
            self.status_color = "#EF4444"  # Red

        # Check for maximum iteration cutoff
        elif self.iteration >= self.max_iters:
            self.is_running = False
            self.btn_pause.label.set_text("Resume")
            self.status_message = f"Max iterations ({self.max_iters}) reached."
            self.status_color = "#F59E0B"  # Amber

        else:
            # Check for oscillatory behavior across valley
            if (self.alpha > 0.5) and (len(self.history_x) >= 3):
                self.status_message = f"Oscillating across minimum... (Step {self.iteration})"
                self.status_color = "#F97316"  # Orange
            else:
                self.status_message = f"Optimizing... (Step {self.iteration})"
                self.status_color = "#38BDF8"  # Sky blue

        # Update step arrow from previous point to current point
        try:
            self.step_arrow.xy = (self.x, self.f(self.x))
            self.step_arrow.set_position((prev_x, self.f(prev_x)))
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # Animation Frame Callback
    # --------------------------------------------------------------------------
    def _on_animation_frame(self, frame_num):
        """FuncAnimation update callback triggered on each timer tick."""
        if self.is_running and not (self.is_converged or self.is_diverged):
            self._perform_step()
            self._render_state()

        return (
            self.line_trajectory,
            self.line_tangent,
            self.scatter_current,
            self.scatter_halo,
            self.line_loss,
            self.stats_text,
            self.point_annot,
        )

    # --------------------------------------------------------------------------
    # Visual Artists Rendering
    # --------------------------------------------------------------------------
    def _render_state(self):
        """Synchronize plot artists and telemetry with current optimization state."""
        # Update Trajectory
        self.line_trajectory.set_data(self.history_x, self.history_y)

        # Update Current Point Marker & Halo
        self.scatter_current.set_offsets([[self.x, self.f(self.x)]])
        self.scatter_halo.set_offsets([[self.x, self.f(self.x)]])

        # Update Annotation
        self.point_annot.xy = (self.x, self.f(self.x))
        self.point_annot.set_text(
            f"$x = {self.x:+.4f}$\n$f(x) = {self.f(self.x):.4f}$"
        )

        # Update Tangent Line
        self._update_tangent_line()

        # Update Loss Curve
        iters = list(range(len(self.history_y)))
        self.line_loss.set_data(iters, self.history_y)

        # Auto-scale Loss Plot
        current_max_loss = max(self.history_y)
        self.ax_loss.set_xlim(0, max(12, self.iteration + 3))
        if current_max_loss > 0:
            self.ax_loss.set_ylim(-0.5, current_max_loss * 1.15)

        # Auto-expand Parabola Plot if points are exiting standard frame
        if abs(self.x) > 5.5 and not self.is_diverged:
            pad = abs(self.x) * 1.25
            self.ax_parabola.set_xlim(-pad, pad)
            self.ax_parabola.set_ylim(-2, (pad ** 2) * 1.05)

        # Update Telemetry & Banner Text
        self._update_telemetry()
        self._update_banner()

    def _update_tangent_line(self):
        """Draw local tangent line segment through (x, f(x)) with slope 2x."""
        if self.is_diverged or abs(self.x) > 50.0:
            self.line_tangent.set_data([], [])
            return

        slope = self.grad_f(self.x)
        tangent_span = 1.6
        x_tan = np.array([self.x - tangent_span, self.x + tangent_span])
        y_tan = self.f(self.x) + slope * (x_tan - self.x)
        self.line_tangent.set_data(x_tan, y_tan)

    def _update_telemetry(self):
        """Render the dark-themed monospace telemetry metrics card."""
        cur_grad = self.grad_f(self.x)
        step_val = -self.alpha * cur_grad

        telemetry_str = (
            "╔═══════════════════════════════════════╗\n"
            "║         OPTIMIZATION TELEMETRY        ║\n"
            "╠═══════════════════════════════════════╣\n"
            f"║ Iteration (t)     : {self.iteration:>3d} / {self.max_iters:<3d}       ║\n"
            f"║ Position (x_t)    : {self.x:>+10.4f}        ║\n"
            f"║ Cost f(x_t)       : {self.f(self.x):>10.4f}        ║\n"
            f"║ Gradient (df/dx)  : {cur_grad:>+10.4f}        ║\n"
            f"║ Step (-α · df/dx) : {step_val:>+10.4f}        ║\n"
            f"║ Learning Rate (α) : {self.alpha:>10.4f}        ║\n"
            "╠═══════════════════════════════════════╣\n"
            f"║ STATUS: {self.status_message:<30s}║\n"
            "╚═══════════════════════════════════════╝"
        )
        self.stats_text.set_text(telemetry_str)

    def _update_banner(self):
        """Update the educational regime commentary banner based on alpha."""
        if self.alpha < 0.10:
            regime = "Small Learning Rate: Slow Convergence"
            insight = (
                "Steps are small and cautious. Convergence is steady and guaranteed, "
                "but requires many iterations to reach x = 0."
            )
            accent = "#1E3A8A"
        elif 0.10 <= self.alpha < 0.45:
            regime = "Appropriate Learning Rate: Faster Convergence"
            insight = (
                "Steps are well-proportioned to the slope. "
                "Moves smoothly and rapidly toward the minimum at x = 0."
            )
            accent = "#166534"
        elif 0.45 <= self.alpha <= 0.55:
            regime = "Optimal Step: 1-Step Convergence"
            insight = (
                "At α = 0.50, the gradient step reaches the global minimum x = 0 in a single iteration!"
            )
            accent = "#3730A3"
        elif 0.55 < self.alpha < 1.00:
            regime = "Excessively Large Learning Rate: Overshooting & Oscillation"
            insight = (
                "Step overshoots the minimum and lands on the opposite wall, "
                "bouncing back and forth across x = 0 while slowly settling."
            )
            accent = "#9A3412"
        elif np.isclose(self.alpha, 1.00, atol=0.015):
            regime = "Excessively Large Learning Rate: Limit Cycle Oscillation"
            insight = (
                "At α = 1.00, every step overshoots to the exact opposite side (-x_t), "
                "bouncing back and forth endlessly without converging."
            )
            accent = "#991B1B"
        else:
            regime = "Excessively Large Learning Rate: Divergence"
            insight = (
                "Severe overshooting! Each step jumps further away from the minimum, "
                "exploding toward ±∞."
            )
            accent = "#7F1D1D"

        banner_content = (
            f"Regime: {regime}\n"
            f"Update Rule: x_(t+1) = x_t - α(2x_t)\n"
            f"Insight: {insight}"
        )
        self.banner_text.set_text(banner_content)
        self.banner_text.set_color(accent)

    # --------------------------------------------------------------------------
    # Interactive Callback Handlers
    # --------------------------------------------------------------------------
    def _on_pause_clicked(self, event):
        """Toggle animation between running and paused."""
        self.is_running = not self.is_running
        self.btn_pause.label.set_text("Pause" if self.is_running else "Resume")
        if not self.is_running and not (self.is_converged or self.is_diverged):
            self.status_message = "Paused by user."
            self.status_color = "#64748B"
        self._update_telemetry()
        self.fig.canvas.draw_idle()

    def _on_step_clicked(self, event):
        """Manually execute exactly one gradient descent iteration."""
        self.is_running = False
        self.btn_pause.label.set_text("Resume")
        self._perform_step()
        self._render_state()
        self.fig.canvas.draw_idle()

    def _on_restart_clicked(self, event):
        """Reset simulation state and restart animation with current sliders."""
        self.restart(x0=self.slider_x0.val, alpha=self.slider_alpha.val)

    def _on_preset_clicked(self, val: float):
        """Load a predefined learning rate preset and trigger a clean restart."""
        self.slider_alpha.set_val(val)
        self.restart(x0=self.slider_x0.val, alpha=val)

    def _on_alpha_slider_changed(self, val: float):
        """Update alpha and refresh educational explanation banner in real time."""
        self.alpha = float(val)
        self._update_telemetry()
        self._update_banner()
        self.fig.canvas.draw_idle()

    def _on_x0_slider_changed(self, val: float):
        """Update x0 starting position. If at iteration 0, reposition marker live."""
        self.x0 = float(val)
        if self.iteration == 0:
            self.x = self.x0
            self.history_x = [self.x0]
            self.history_y = [self.f(self.x0)]
            self.history_grad = [self.grad_f(self.x0)]
            self._render_state()
            self.fig.canvas.draw_idle()

    def _on_speed_slider_changed(self, val: float):
        """Adjust animation tick interval dynamically."""
        self.interval_ms = int(val)
        if hasattr(self.anim, "event_source") and self.anim.event_source is not None:
            self.anim.event_source.interval = self.interval_ms

    def restart(self, x0: float = None, alpha: float = None):
        """
        Cleanly reset all internal state and plot artists.
        Avoids creating multiple FuncAnimation timers to prevent overlapping updates.
        """
        if x0 is not None:
            self.x0 = float(x0)
        if alpha is not None:
            self.alpha = float(alpha)

        # Reset State
        self.x = self.x0
        self.iteration = 0
        self.history_x = [self.x0]
        self.history_y = [self.f(self.x0)]
        self.history_grad = [self.grad_f(self.x0)]

        self.is_converged = False
        self.is_diverged = False
        self.is_running = True
        self.btn_pause.label.set_text("Pause")
        self.status_message = "Restarted. Running..."
        self.status_color = "#38BDF8"

        # Reset Axes Bounds
        pad = max(6.5, abs(self.x0) * 1.25)
        self.ax_parabola.set_xlim(-pad, pad)
        self.ax_parabola.set_ylim(-2, max(42, (pad ** 2) * 1.05))

        self.ax_loss.set_xlim(0, 15)
        self.ax_loss.set_ylim(0, max(26, self.f(self.x0) * 1.15))

        # Reset Step Arrow
        try:
            self.step_arrow.xy = (self.x, self.f(self.x))
            self.step_arrow.set_position((self.x, self.f(self.x)))
        except Exception:
            pass

        self._render_state()
        self.fig.canvas.draw_idle()


def main():
    """Application entry point."""
    print("=" * 76)
    print("  Interactive Gradient Descent Animation: Minimizing f(x) = x²")
    print("=" * 76)
    print("Controls:")
    print("  • Learning Rate Slider: Adjust α continuously from 0.01 to 1.15.")
    print("  • Initial x₀ Slider   : Move starting point from -6.0 to +6.0.")
    print("  • Speed Slider        : Control animation delay (50ms to 800ms).")
    print("  • Pause/Resume Button : Freeze or continue the descent.")
    print("  • Step (+1) Button    : Manually advance single iterations.")
    print("  • Restart Button      : Reset animation with current parameters.")
    print("  • Presets Row         : Fast exploration of Slow, Optimal, 1-Step,")
    print("                          Oscillating, and Diverging regimes.")
    print("=" * 76)

    # Launch visualizer with sensible defaults: x0 = 5.0, alpha = 0.15
    visualizer = GradientDescentVisualizer(x0=5.0, alpha=0.15)
    plt.show()
    return visualizer


if __name__ == "__main__":
    main()
