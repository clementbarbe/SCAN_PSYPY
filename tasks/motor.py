"""
Motor SCAN Task — two paradigms for fMRI.

Task 1: 3 conditions (RH, LH, RF), 12 trials/run, 202s exact.
Task 2: 6 conditions (3 simple + 3 combined), 32 trials/run, 630s exact.

Green blinking cross at 1.25 Hz during movement phase.
Jitters auto-adjusted so total run duration is exact.
"""

from __future__ import annotations

import random
from pathlib import Path
from collections import Counter

from psychopy import visual

from tasks.base import BaseTask
from tasks.registry import register_task
from tasks.utils.sequence import desequence
from utils.console import SYM_PAUSE
from config.constants import PROJECT_ROOT


@register_task('motor')
class MotorTask(BaseTask):
    """Motor SCAN fMRI task."""

    TASK_NAME = 'motor'

    # ═════════════════════════════════════════════════════════════════
    # SETUP
    # ═════════════════════════════════════════════════════════════════

    def _setup_stimuli(self) -> None:
        stim_cfg = self.task_config.get('stimulus', {})

        self._green_cross = visual.TextStim(
            self.win, text='+',
            color=stim_cfg.get('green_color', [0, 1, 0]),
            height=stim_cfg.get('fixation_height', 0.12),
            pos=(0, 0), bold=True,
        )
        self._white_cross = visual.TextStim(
            self.win, text='+', color='white',
            height=stim_cfg.get('fixation_height', 0.12),
            pos=(0, 0), bold=True,
        )

        self._instr_text = visual.TextStim(
            self.win, text='', color='white',
            height=stim_cfg.get('instruction_height', 0.08),
            pos=(0, stim_cfg.get('text_y', -0.25)),
            bold=True, font='monospace',
        )

        self._blink_freq = stim_cfg.get('blink_freq', 1.25)
        self._blink_period = 1.0 / self._blink_freq

        # Load images
        img_cfg = self.task_config.get('images', {})
        img_size = stim_cfg.get('image_size', [0.4, 0.4])
        img_y = stim_cfg.get('image_y', 0.15)

        self._images = {}
        for key, rel_path in img_cfg.items():
            full_path = PROJECT_ROOT / rel_path
            if full_path.exists():
                self._images[key] = visual.ImageStim(
                    self.win, image=str(full_path),
                    size=img_size, pos=(0, img_y),
                )
            else:
                self.logger.warn(f"Image not found: {full_path}")
                self._images[key] = visual.TextStim(
                    self.win, text=f'[{key}]', color='yellow',
                    height=0.06, pos=(0, img_y),
                )

        self._conditions_t1 = self.task_config.get('conditions_task1', [])
        self._conditions_t2 = self.task_config.get('conditions_task2', [])
        self._ttl = self.task_config.get('ttl_codes', {})

    # ═════════════════════════════════════════════════════════════════
    # INSTRUCTIONS
    # ═════════════════════════════════════════════════════════════════

    def _get_instruction_text(self) -> str:
        task_type = self.design.get('task_type', 1)
        run_num = self.design.get('run_number', 1)
        dur = self.design.get('total_duration', 0)
        dur_min = int(dur) // 60
        dur_sec = int(dur) % 60

        if task_type == 1:
            return (
                f"Tache Motrice 1 — Run {run_num}\n"
                f"Duree : {dur_min}min{dur_sec:02d}s\n\n"
                f"1 - Vous verrez une image indiquant\n"
                f"    quel membre bouger\n\n"
                f"2 - Une croix blanche apparait :\n"
                f"    pensez au mouvement a effectuer\n"
                f"    (flexion-extension),\n"
                f"    mais NE BOUGEZ PAS encore\n\n"
                f"3 - Croix verte qui clignote :\n"
                f"    commencez a bouger votre membre\n"
                f"    (flexion-extension) en suivant\n"
                f"    le rythme du clignotement\n\n"
                f"4 - Arretez-vous quand la croix disparait\n\n"
                f"Appuyez sur une touche pour continuer..."
            )
        else:
            return (
                f"Tache Motrice 2 — Run {run_num}\n"
                f"Duree : {dur_min}min{dur_sec:02d}s\n\n"
                f"1 - Vous verrez une ou deux images\n"
                f"    indiquant quel(s) membre(s) bouger\n\n"
                f"2 - Une croix blanche apparait :\n"
                f"    pensez au(x) mouvement(s) a effectuer\n"
                f"    (flexion-extension),\n"
                f"    mais NE BOUGEZ PAS encore\n\n"
                f"3 - Croix verte qui clignote :\n"
                f"    commencez a bouger votre/vos membre(s)\n"
                f"    (flexion-extension) en suivant\n"
                f"    le rythme du clignotement\n\n"
                f"4 - Arretez-vous quand la croix disparait\n\n"
                f"Appuyez sur une touche pour continuer..."
            )

    def _get_block_instruction(self, block_idx: int,
                               block_def: dict) -> str | None:
        return None

    # ═════════════════════════════════════════════════════════════════
    # TRIAL GENERATION
    # ═════════════════════════════════════════════════════════════════

    def generate_trials(self, block_def: dict) -> list:
        task_type = self.design.get('task_type', 1)
        if task_type == 1:
            return self._generate_task1_trials()
        else:
            return self._generate_task2_trials()

    def _generate_task1_trials(self) -> list:
        n_trials = self.design.get('n_trials', 12)
        reps = self.design.get('reps_per_condition', 4)
        instr_durs = self.design.get('instruction_durations', [2.25, 2.5, 2.75])
        mov_dur = self.design.get('movement_duration', 8.0)
        rest_dur = self.design.get('rest_duration', 6.0)
        final_rest = self.design.get('final_rest_duration', 12.0)
        total_target = self.design.get('total_duration', 202.0)
        pre_wait = self.design.get('pre_start_wait', 5.0)

        conditions = self._conditions_t1
        trials = []
        for cond in conditions:
            for _ in range(reps):
                trials.append(cond)

        trials = desequence(
            trials, key_func=lambda t: t['name'], max_consecutive=1,
        )

        instr_assignments = (instr_durs * (n_trials // len(instr_durs) + 1))[:n_trials]
        random.shuffle(instr_assignments)

        fixed_time = pre_wait + (n_trials - 1) * rest_dur + final_rest + n_trials * mov_dur
        total_instr = sum(instr_assignments)
        current_total = fixed_time + total_instr

        diff = total_target - current_total
        if abs(diff) > 0.001:
            adj = diff / n_trials
            instr_assignments = [d + adj for d in instr_assignments]

        result = []
        for i, (cond, instr_dur) in enumerate(zip(trials, instr_assignments)):
            is_last = (i == n_trials - 1)
            result.append({
                'condition': cond,
                'instruction_duration': round(instr_dur, 4),
                'movement_duration': mov_dur,
                'rest_duration': final_rest if is_last else rest_dur,
                'planning_duration': 0.0,
                'task_type': 1,
            })

        return result

    def _generate_task2_trials(self) -> list:
        n_trials = self.design.get('n_trials', 32)
        instr_dur = self.design.get('instruction_duration_fixed', 1.5)
        plan_mean = self.design.get('planning_duration_mean', 4.0)
        plan_jitter = self.design.get('planning_jitter', 0.5)
        mov_dur = self.design.get('movement_duration', 8.0)
        rest_dur = self.design.get('rest_duration', 6.0)
        final_rest = self.design.get('final_rest_duration', 12.0)
        total_target = self.design.get('total_duration', 630.0)
        pre_wait = self.design.get('pre_start_wait', 5.0)

        conditions = self._conditions_t2
        n_conds = len(conditions)

        base_count = n_trials // n_conds
        remainder = n_trials % n_conds
        trials = []
        for i, cond in enumerate(conditions):
            count = base_count + (1 if i < remainder else 0)
            for _ in range(count):
                trials.append(cond)

        trials = desequence(
            trials, key_func=lambda t: t['name'], max_consecutive=1,
        )

        plan_durs = [
            round(random.uniform(plan_mean - plan_jitter,
                                 plan_mean + plan_jitter), 4)
            for _ in range(n_trials)
        ]

        fixed_time = (
            pre_wait
            + n_trials * instr_dur
            + n_trials * mov_dur
            + (n_trials - 1) * rest_dur
            + final_rest
        )
        total_planning = sum(plan_durs)
        current_total = fixed_time + total_planning

        diff = total_target - current_total
        if abs(diff) > 0.001:
            adj = diff / n_trials
            plan_durs = [d + adj for d in plan_durs]

        result = []
        for i, (cond, plan_dur) in enumerate(zip(trials, plan_durs)):
            is_last = (i == n_trials - 1)
            result.append({
                'condition': cond,
                'instruction_duration': instr_dur,
                'planning_duration': round(plan_dur, 4),
                'movement_duration': mov_dur,
                'rest_duration': final_rest if is_last else rest_dur,
                'task_type': 2,
            })

        return result

    # ═════════════════════════════════════════════════════════════════
    # MAIN RUN
    # ═════════════════════════════════════════════════════════════════

    def run(self) -> Path | None:
        saved_path = None
        try:
            self.show_text_and_wait(self._get_instruction_text())
            self.wait_for_trigger()

            pre_wait = self.design.get('pre_start_wait', 5.0)
            if pre_wait > 0:
                self.show_fixation(pre_wait)

            block_def = self.block_sequence[0] if self.block_sequence else {'n_trials': 0}
            trials = self.generate_trials(block_def)

            task_type = self.design.get('task_type', 1)
            run_num = self.design.get('run_number', 1)
            self.logger.log(
                f"Motor Task {task_type} Run {run_num}: "
                f"{len(trials)} trials"
            )

            for trial_idx, trial_data in enumerate(trials):
                record = self.run_trial(
                    trial_data, block_idx=0,
                    trial_idx=trial_idx, block_def=block_def,
                )
                record['trial_idx_global'] = self._global_trial_idx
                self._global_trial_idx += 1
                self.data_writer.write_trial(record)
                self.event_bus.publish('trial_end', record=record)

            total_t = self.clock.time
            target = self.design.get('total_duration', 0)
            self.logger.ok(
                f"Motor Task {task_type} Run {run_num} done. "
                f"Actual: {total_t:.3f}s (target: {target:.1f}s, "
                f"diff: {total_t - target:+.3f}s)"
            )

        except Exception as e:
            from core.exceptions import AbortExperiment
            if isinstance(e, AbortExperiment):
                self.logger.warn(f"ABORT: {e}")
            elif isinstance(e, (KeyboardInterrupt, SystemExit)):
                self.logger.warn("Interrupted.")
            else:
                self.logger.err(f"CRITICAL: {e}")
                import traceback
                traceback.print_exc()

        finally:
            saved_path = self._finish()

        return saved_path

    # ═════════════════════════════════════════════════════════════════
    # TRIAL EXECUTION
    # ═════════════════════════════════════════════════════════════════

    def run_trial(self, trial_data, block_idx: int, trial_idx: int,
                  block_def: dict, **kwargs) -> dict:

        cond = trial_data['condition']
        cond_name = cond['name']
        cond_images = cond['images']
        task_type = trial_data['task_type']

        instr_dur = trial_data['instruction_duration']
        plan_dur = trial_data.get('planning_duration', 0.0)
        mov_dur = trial_data['movement_duration']
        rest_dur = trial_data['rest_duration']

        self.flush_keyboard()

        # ── Phase 1: Instruction ─────────────────────────────────────
        ttl = self._ttl.get('instruction_onset', 0)
        if ttl:
            self.hardware.send_trigger(ttl)

        instr_onset = self.clock.time
        self.hardware.send_eyetracker_message(
            f"INSTR_{cond_name}_T{trial_idx}_t{instr_onset:.3f}"
        )

        self._show_instruction(cond_name, cond_images, instr_dur)

        # ── Phase 2: Planning (Task 2 only) ──────────────────────────
        plan_onset = -1.0
        if task_type == 2 and plan_dur > 0:
            plan_onset = self.clock.time
            self.hardware.send_eyetracker_message(
                f"PLAN_{cond_name}_T{trial_idx}_t{plan_onset:.3f}"
            )
            self._show_white_cross(plan_dur)

        # ── Phase 3: Movement ────────────────────────────────────────
        ttl = self._ttl.get('movement_onset', 0)
        if ttl:
            self.hardware.send_trigger(ttl)

        mov_onset = self.clock.time
        self.hardware.send_eyetracker_message(
            f"MOV_{cond_name}_T{trial_idx}_t{mov_onset:.3f}"
        )

        self._show_blinking_cross(mov_dur)

        # ── Phase 4: Rest ────────────────────────────────────────────
        ttl = self._ttl.get('rest_onset', 0)
        if ttl:
            self.hardware.send_trigger(ttl)

        rest_onset = self.clock.time
        self._show_black_screen(rest_dur)

        # ── Record ───────────────────────────────────────────────────
        record = self._base_record(block_idx, trial_idx, block_def)
        record.update({
            'task_type': task_type,
            'run_number': self.design.get('run_number', 1),
            'condition': cond_name,
            'condition_images': ','.join(cond_images),
            'instruction_onset': round(instr_onset, 4),
            'instruction_duration': round(instr_dur, 4),
            'planning_onset': round(plan_onset, 4) if plan_onset >= 0 else -1,
            'planning_duration': round(plan_dur, 4),
            'movement_onset': round(mov_onset, 4),
            'movement_duration': round(mov_dur, 4),
            'rest_onset': round(rest_onset, 4),
            'rest_duration': round(rest_dur, 4),
            'stim_onset': round(instr_onset, 4),
        })

        # Console
        if task_type == 2:
            print(
                f"  T{trial_idx:02d} | t={instr_onset:8.3f}s | "
                f"{cond_name:>28s} | "
                f"instr={instr_dur:.2f}s plan={plan_dur:.2f}s"
            )
        else:
            print(
                f"  T{trial_idx:02d} | t={instr_onset:8.3f}s | "
                f"{cond_name:>28s} | "
                f"instr={instr_dur:.2f}s"
            )

        return record

    # ═════════════════════════════════════════════════════════════════
    # DISPLAY PHASES
    # ═════════════════════════════════════════════════════════════════

    def _show_instruction(self, name: str, image_keys: list[str],
                          duration: float) -> None:
        """
        Show condition name + image(s).

        Single image: centered.
        Two images: left body part on left side, right body part on right side.
            - left_hand  → always left position
            - right_hand → always right position
            - right_foot → always right position
        """
        deadline = self.clock.time + duration

        # Determine image positions for dual display
        if len(image_keys) == 2:
            # Sort: left-side body parts go left, right-side go right
            left_keys = {'left_hand'}
            right_keys = {'right_hand', 'right_foot'}

            img_left = None
            img_right = None

            for key in image_keys:
                if key in left_keys:
                    img_left = self._images.get(key)
                elif key in right_keys:
                    img_right = self._images.get(key)

            # Fallback if both are same side (shouldn't happen)
            if img_left is None and img_right is None:
                img_left = self._images.get(image_keys[0])
                img_right = self._images.get(image_keys[1])
            elif img_left is None:
                img_left = self._images.get(
                    [k for k in image_keys
                     if self._images.get(k) is not img_right][0]
                )
            elif img_right is None:
                img_right = self._images.get(
                    [k for k in image_keys
                     if self._images.get(k) is not img_left][0]
                )

        while self.clock.time < deadline:
            if len(image_keys) == 1:
                img = self._images.get(image_keys[0])
                if img:
                    img.pos = (0, 0.15)
                    img.draw()

            elif len(image_keys) >= 2:
                if img_left:
                    img_left.pos = (-0.25, 0.15)
                    img_left.draw()
                if img_right:
                    img_right.pos = (0.25, 0.15)
                    img_right.draw()

            self._instr_text.text = name
            self._instr_text.draw()
            self.win.flip()
            self.get_keys(key_list=[])

    def _show_white_cross(self, duration: float) -> None:
        deadline = self.clock.time + duration
        while self.clock.time < deadline:
            self._white_cross.draw()
            self.win.flip()
            self.get_keys(key_list=[])

    def _show_blinking_cross(self, duration: float) -> None:
        start = self.clock.time
        deadline = start + duration
        half_period = self._blink_period / 2.0

        while self.clock.time < deadline:
            elapsed = self.clock.time - start
            phase = elapsed % self._blink_period
            visible = phase < half_period

            if visible:
                self._green_cross.draw()

            self.win.flip()
            self.get_keys(key_list=[])

    def _show_black_screen(self, duration: float) -> None:
        deadline = self.clock.time + duration
        while self.clock.time < deadline:
            self.win.flip()
            self.get_keys(key_list=[])

    # ═════════════════════════════════════════════════════════════════
    # STATS
    # ═════════════════════════════════════════════════════════════════

    def _print_task_stats(self) -> None:
        records = self.data_writer.records
        if not records:
            return

        task_type = records[0].get('task_type', 1)
        run_num = records[0].get('run_number', 1)
        total = len(records)

        last = records[-1]
        actual_dur = last['rest_onset'] + last['rest_duration']
        target_dur = self.design.get('total_duration', 0)

        print(f"\n{'=' * 60}")
        print(
            f"  MOTOR TASK {task_type} RUN {run_num} — "
            f"{total} essais"
        )
        print(
            f"  Duree : {actual_dur:.1f}s "
            f"(cible: {target_dur:.1f}s, "
            f"ecart: {actual_dur - target_dur:+.3f}s)"
        )
        print(f"  {'-' * 54}")

        cond_counts = Counter(r['condition'] for r in records)
        for cond, count in sorted(cond_counts.items()):
            print(f"  {cond:>28s}: {count} essais")

        if task_type == 1:
            instr_durs = [r['instruction_duration'] for r in records]
            print(f"  {'-' * 54}")
            print(
                f"  Jitter instructions: "
                f"min={min(instr_durs):.3f}s "
                f"max={max(instr_durs):.3f}s "
                f"mean={sum(instr_durs)/len(instr_durs):.3f}s"
            )
        elif task_type == 2:
            plan_durs = [r['planning_duration'] for r in records]
            print(f"  {'-' * 54}")
            print(
                f"  Jitter planning: "
                f"min={min(plan_durs):.3f}s "
                f"max={max(plan_durs):.3f}s "
                f"mean={sum(plan_durs)/len(plan_durs):.3f}s"
            )

        print(f"{'=' * 60}\n")