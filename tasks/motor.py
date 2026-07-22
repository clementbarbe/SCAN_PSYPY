"""
Motor SCAN Task — Isolated & Combined paradigms for fMRI.

Isolated Task: 3 conditions (Main Droite, Main Gauche, Pied Droit),
               36 trials, 1 run.
Combined Task: 6 conditions (3 simple + 3 combined),
               32 trials/run, 3 runs.

All timings precalculated as absolute deadlines.
Instruction durations for Isolated Task: exactly 2.25, 2.50, or 2.75s.
Planning durations for Combined Task: 4.0 ± 0.5s, mean forced to 4.0s.
"""

from __future__ import annotations

import random
from pathlib import Path
from collections import Counter
from datetime import datetime

from psychopy import visual

from tasks.base import BaseTask
from tasks.registry import register_task
from tasks.utils.sequence import desequence
from config.constants import PROJECT_ROOT


@register_task('motor')
class MotorTask(BaseTask):
    """Motor SCAN fMRI task with precalculated absolute timings."""

    TASK_NAME = 'motor'

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
                f"Mouvement Isole\n"
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
                f"Mouvement Combine — Run {run_num}\n"
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

    def _get_block_instruction(self, block_idx, block_def):
        return None

    # ═════════════════════════════════════════════════════════════════
    # PRECALCULATE
    # ═════════════════════════════════════════════════════════════════

    def _precalculate_schedule(self) -> list[dict]:
        task_type = self.design.get('task_type', 1)

        if task_type == 1:
            trials = self._build_task1_trials()
        else:
            trials = self._build_task2_trials()

        pre_wait = self.design.get('pre_start_wait', 5.0)
        total_target = self.design.get('total_duration', 602.0)

        t = pre_wait
        schedule = []

        for i, trial in enumerate(trials):
            entry = dict(trial)

            entry['abs_instr_onset'] = round(t, 6)
            t += entry['instruction_duration']

            if entry.get('planning_duration', 0) > 0:
                entry['abs_plan_onset'] = round(t, 6)
                t += entry['planning_duration']
            else:
                entry['abs_plan_onset'] = -1.0

            entry['abs_mov_onset'] = round(t, 6)
            t += entry['movement_duration']

            entry['abs_rest_onset'] = round(t, 6)
            t += entry['rest_duration']

            entry['abs_trial_end'] = round(t, 6)
            schedule.append(entry)

        actual_total = schedule[-1]['abs_trial_end']
        drift = actual_total - total_target
        if abs(drift) > 0.01:
            self.logger.warn(
                f"Schedule drift: {drift:+.3f}s "
                f"(actual={actual_total:.3f}s target={total_target:.1f}s)"
            )

        self.logger.log(
            f"Schedule: {len(schedule)} trials, "
            f"total={actual_total:.3f}s (target={total_target:.1f}s)"
        )
        return schedule

    def _build_task1_trials(self) -> list[dict]:
        n_trials = self.design.get('n_trials', 36)
        reps = self.design.get('reps_per_condition', 12)
        instr_pool = self.design.get(
            'instruction_durations', [2.25, 2.50, 2.75]
        )
        mov_dur = self.design.get('movement_duration', 8.0)
        rest_dur = self.design.get('rest_duration', 6.0)
        final_rest = self.design.get('final_rest_duration', 12.0)
        total_target = self.design.get('total_duration', 602.0)
        pre_wait = self.design.get('pre_start_wait', 5.0)

        conditions = self._conditions_t1
        trial_conds = []
        for cond in conditions:
            for _ in range(reps):
                trial_conds.append(cond)

        trial_conds = desequence(
            trial_conds, key_func=lambda t: t['name'], max_consecutive=2,
        )

        # EXACT instruction durations, balanced
        per_dur = n_trials // len(instr_pool)
        remainder = n_trials % len(instr_pool)
        assignments = []
        for i, d in enumerate(instr_pool):
            count = per_dur + (1 if i < remainder else 0)
            assignments.extend([d] * count)
        random.shuffle(assignments)

        # Adjust REST to hit total (never touch instructions)
        task_content = sum(assignments) + n_trials * mov_dur
        rest_content = (n_trials - 1) * rest_dur + final_rest
        computed = pre_wait + task_content + rest_content

        diff = total_target - computed
        n_rests = n_trials
        adj = diff / n_rests if abs(diff) > 0.001 else 0
        rest_adj = rest_dur + adj
        final_adj = final_rest + adj

        if abs(adj) > 0.001:
            self.logger.log(f"Isolated: rest adj {adj*1000:+.1f}ms/rest")

        trials = []
        for i, (cond, instr_d) in enumerate(zip(trial_conds, assignments)):
            is_last = (i == n_trials - 1)
            trials.append({
                'condition': cond,
                'instruction_duration': instr_d,
                'planning_duration': 0.0,
                'movement_duration': mov_dur,
                'rest_duration': round(final_adj if is_last else rest_adj, 4),
                'task_type': 1,
            })
        return trials

    def _build_task2_trials(self) -> list[dict]:
        n_trials = self.design.get('n_trials', 32)
        instr_dur = self.design.get('instruction_duration_fixed', 1.5)
        plan_mean = self.design.get('planning_duration_mean', 4.0)
        plan_jitter = self.design.get('planning_jitter', 0.5)
        mov_dur = self.design.get('movement_duration', 8.0)
        rest_dur = self.design.get('rest_duration', 6.0)
        final_rest = self.design.get('final_rest_duration', 12.0)
        total_target = self.design.get('total_duration', 635.0)
        pre_wait = self.design.get('pre_start_wait', 5.0)

        conditions = self._conditions_t2
        n_conds = len(conditions)

        base_count = n_trials // n_conds
        remainder = n_trials % n_conds
        trial_conds = []
        for i, cond in enumerate(conditions):
            count = base_count + (1 if i < remainder else 0)
            for _ in range(count):
                trial_conds.append(cond)

        trial_conds = desequence(
            trial_conds, key_func=lambda t: t['name'], max_consecutive=1,
        )

        # Planning: mean forced to exactly plan_mean
        plan_durs = [
            random.uniform(plan_mean - plan_jitter, plan_mean + plan_jitter)
            for _ in range(n_trials)
        ]
        correction = plan_mean - sum(plan_durs) / len(plan_durs)
        plan_durs = [
            max(plan_mean - plan_jitter,
                min(plan_mean + plan_jitter, d + correction))
            for d in plan_durs
        ]

        # Adjust REST for exact total
        task_content = n_trials * instr_dur + sum(plan_durs) + n_trials * mov_dur
        rest_content = (n_trials - 1) * rest_dur + final_rest
        computed = pre_wait + task_content + rest_content

        diff = total_target - computed
        n_rests = n_trials
        adj = diff / n_rests if abs(diff) > 0.001 else 0
        rest_adj = rest_dur + adj
        final_adj = final_rest + adj

        if abs(adj) > 0.001:
            self.logger.log(f"Combined: rest adj {adj*1000:+.1f}ms/rest")

        trials = []
        for i, (cond, plan_d) in enumerate(zip(trial_conds, plan_durs)):
            is_last = (i == n_trials - 1)
            trials.append({
                'condition': cond,
                'instruction_duration': instr_dur,
                'planning_duration': round(plan_d, 4),
                'movement_duration': mov_dur,
                'rest_duration': round(final_adj if is_last else rest_adj, 4),
                'task_type': 2,
            })
        return trials

    # ═════════════════════════════════════════════════════════════════
    # MAIN RUN
    # ═════════════════════════════════════════════════════════════════

    def run(self) -> Path | None:
        saved_path = None
        try:
            self.show_text_and_wait(self._get_instruction_text())

            self.logger.log("Precalculating schedule...")
            schedule = self._precalculate_schedule()
            self.logger.ok(f"Schedule ready: {len(schedule)} trials")

            self.wait_for_trigger()

            pre_wait = self.design.get('pre_start_wait', 5.0)
            if pre_wait > 0:
                self._run_until(pre_wait, 'fixation')

            task_type = self.design.get('task_type', 1)
            run_num = self.design.get('run_number', 1)
            block_def = self.block_sequence[0] if self.block_sequence else {'n_trials': 0}
            task_label = "Isolated" if task_type == 1 else "Combined"

            self.logger.log(f"{task_label} Run {run_num}: {len(schedule)} trials")

            for trial_idx, entry in enumerate(schedule):
                records = self._execute_trial(entry, trial_idx, block_def)
                for record in records:
                    record['trial_idx_global'] = self._global_trial_idx
                    self.data_writer.write_trial(record)
                self._global_trial_idx += 1
                self.event_bus.publish('trial_end', record=records[0])

            total_t = self.clock.time
            target = self.design.get('total_duration', 0)
            self.logger.ok(
                f"{task_label} Run {run_num} done. "
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

    def _execute_trial(self, entry: dict, trial_idx: int,
                       block_def: dict) -> list[dict]:

        cond = entry['condition']
        cond_name = cond['name']
        cond_images = cond['images']
        task_type = entry['task_type']

        abs_instr = entry['abs_instr_onset']
        abs_plan = entry['abs_plan_onset']
        abs_mov = entry['abs_mov_onset']
        abs_rest = entry['abs_rest_onset']
        abs_end = entry['abs_trial_end']

        instr_dur = entry['instruction_duration']
        plan_dur = entry.get('planning_duration', 0.0)
        mov_dur = entry['movement_duration']
        rest_dur = entry['rest_duration']

        self.flush_keyboard()
        records = []

        def make_base():
            return {
                'participant': self.settings.participant_id,
                'session': self.settings.session,
                'run': self.settings.run,
                'scanner': self.scanner.name,
                'mode': self.settings.mode,
                'design_id': self.design_id,
                'design_name': self.design.get('name', ''),
                'trigger_time': self.clock.trigger_wall_time or '',
                'task_type': task_type,
                'run_number': self.design.get('run_number', 1),
                'trial_idx': trial_idx,
                'condition': cond_name,
                'condition_images': ','.join(cond_images),
                'wall_timestamp': datetime.now().strftime('%H:%M:%S.%f'),
            }

        # Instruction
        ttl = self._ttl.get('instruction_onset', 0)
        if ttl:
            self.hardware.send_trigger(ttl)
        self.hardware.send_eyetracker_message(
            f"INSTR_{cond_name}_T{trial_idx}_t{abs_instr:.3f}"
        )

        actual_instr = self.clock.time
        next_deadline = abs_plan if abs_plan >= 0 else abs_mov
        self._show_instruction_until(cond_name, cond_images, next_deadline)

        rec = make_base()
        rec.update({
            'event_type': 'instruction',
            'event_onset': round(actual_instr, 4),
            'event_duration': round(instr_dur, 4),
            'scheduled_onset': round(abs_instr, 4),
            'stim_onset': round(actual_instr, 4),
            'task_time': round(self.clock.time, 4),
        })
        records.append(rec)

        # Planning (combined only)
        if task_type == 2 and plan_dur > 0:
            self.hardware.send_eyetracker_message(
                f"PLAN_{cond_name}_T{trial_idx}_t{abs_plan:.3f}"
            )
            actual_plan = self.clock.time
            self._run_until(abs_mov, 'white_cross')

            rec = make_base()
            rec.update({
                'event_type': 'planning',
                'event_onset': round(actual_plan, 4),
                'event_duration': round(plan_dur, 4),
                'scheduled_onset': round(abs_plan, 4),
                'stim_onset': round(actual_plan, 4),
                'task_time': round(self.clock.time, 4),
            })
            records.append(rec)

        # Movement
        ttl = self._ttl.get('movement_onset', 0)
        if ttl:
            self.hardware.send_trigger(ttl)
        self.hardware.send_eyetracker_message(
            f"MOV_{cond_name}_T{trial_idx}_t{abs_mov:.3f}"
        )

        actual_mov = self.clock.time
        self._run_until(abs_rest, 'blink')

        rec = make_base()
        rec.update({
            'event_type': 'movement',
            'event_onset': round(actual_mov, 4),
            'event_duration': round(mov_dur, 4),
            'scheduled_onset': round(abs_mov, 4),
            'stim_onset': round(actual_mov, 4),
            'task_time': round(self.clock.time, 4),
        })
        records.append(rec)

        # Rest
        ttl = self._ttl.get('rest_onset', 0)
        if ttl:
            self.hardware.send_trigger(ttl)

        actual_rest = self.clock.time
        self._run_until(abs_end, 'black')

        rec = make_base()
        rec.update({
            'event_type': 'rest',
            'event_onset': round(actual_rest, 4),
            'event_duration': round(rest_dur, 4),
            'scheduled_onset': round(abs_rest, 4),
            'stim_onset': round(actual_rest, 4),
            'task_time': round(self.clock.time, 4),
        })
        records.append(rec)

        # Console
        if task_type == 2:
            print(
                f"  T{trial_idx:02d} | t={actual_instr:8.3f}s | "
                f"{cond_name:>28s} | "
                f"instr={instr_dur:.2f}s plan={plan_dur:.2f}s"
            )
        else:
            print(
                f"  T{trial_idx:02d} | t={actual_instr:8.3f}s | "
                f"{cond_name:>28s} | "
                f"instr={instr_dur:.2f}s"
            )

        return records

    # ═════════════════════════════════════════════════════════════════
    # DISPLAY
    # ═════════════════════════════════════════════════════════════════

    def _run_until(self, abs_deadline: float, mode: str) -> None:
        blink_start = self.clock.time

        while self.clock.time < abs_deadline:
            if mode == 'fixation':
                self._fixation.draw()
            elif mode == 'white_cross':
                self._white_cross.draw()
            elif mode == 'blink':
                elapsed = self.clock.time - blink_start
                phase = elapsed % self._blink_period
                if phase < self._blink_period / 2.0:
                    self._green_cross.draw()
            elif mode == 'black':
                pass

            self.win.flip()
            self.get_keys(key_list=[])

    def _show_instruction_until(self, name: str, image_keys: list[str],
                                abs_deadline: float) -> None:
        left_keys = {'main_gauche'}
        right_keys = {'main_droite', 'pied_droit'}

        img_positions = []
        if len(image_keys) == 1:
            img = self._images.get(image_keys[0])
            if img:
                img_positions.append((img, (0, 0.15)))
        elif len(image_keys) >= 2:
            img_left = None
            img_right = None
            for key in image_keys:
                if key in left_keys:
                    img_left = self._images.get(key)
                elif key in right_keys:
                    if img_right is None:
                        img_right = self._images.get(key)
                    else:
                        img_left = self._images.get(key)
            if img_left is None and img_right is None:
                img_left = self._images.get(image_keys[0])
                img_right = self._images.get(image_keys[1])
            elif img_left is None:
                for k in image_keys:
                    if self._images.get(k) is not img_right:
                        img_left = self._images.get(k)
                        break
            elif img_right is None:
                for k in image_keys:
                    if self._images.get(k) is not img_left:
                        img_right = self._images.get(k)
                        break
            if img_left:
                img_positions.append((img_left, (-0.25, 0.15)))
            if img_right:
                img_positions.append((img_right, (0.25, 0.15)))

        self._instr_text.text = name

        while self.clock.time < abs_deadline:
            for img, pos in img_positions:
                img.pos = pos
                img.draw()
            self._instr_text.draw()
            self.win.flip()
            self.get_keys(key_list=[])

    def generate_trials(self, block_def):
        return []

    def run_trial(self, trial_data, block_idx, trial_idx, block_def, **kw):
        return {}

    # ═════════════════════════════════════════════════════════════════
    # STATS
    # ═════════════════════════════════════════════════════════════════

    def _print_task_stats(self) -> None:
        records = self.data_writer.records
        if not records:
            return

        task_type = records[0].get('task_type', 1)
        run_num = records[0].get('run_number', 1)
        task_label = "ISOLATED" if task_type == 1 else "COMBINED"

        instr_recs = [r for r in records if r.get('event_type') == 'instruction']
        total_trials = len(instr_recs)

        rest_recs = [r for r in records if r.get('event_type') == 'rest']
        if rest_recs:
            last = rest_recs[-1]
            actual_dur = last['event_onset'] + last['event_duration']
        else:
            actual_dur = records[-1].get('task_time', 0)

        target_dur = self.design.get('total_duration', 0)

        print(f"\n{'=' * 60}")
        print(f"  {task_label} RUN {run_num} — {total_trials} essais")
        print(
            f"  Duree : {actual_dur:.1f}s "
            f"(cible: {target_dur:.1f}s, "
            f"ecart: {actual_dur - target_dur:+.3f}s)"
        )
        print(f"  {'-' * 54}")

        cond_counts = Counter(r['condition'] for r in instr_recs)
        for cond, count in sorted(cond_counts.items()):
            print(f"  {cond:>28s}: {count} essais")

        print(f"  {'-' * 54}")

        if task_type == 1:
            durs = [r['event_duration'] for r in instr_recs]
            print(
                f"  Instructions: "
                f"min={min(durs):.3f}s max={max(durs):.3f}s "
                f"mean={sum(durs)/len(durs):.3f}s"
            )

        plan_recs = [r for r in records if r.get('event_type') == 'planning']
        if plan_recs:
            durs = [r['event_duration'] for r in plan_recs]
            print(
                f"  Planning: "
                f"min={min(durs):.3f}s max={max(durs):.3f}s "
                f"mean={sum(durs)/len(durs):.3f}s"
            )

        all_events = [r for r in records if r.get('scheduled_onset', -1) >= 0]
        if all_events:
            drifts = [abs(r['event_onset'] - r['scheduled_onset']) for r in all_events]
            if drifts:
                print(
                    f"  Precision: max={max(drifts)*1000:.1f}ms "
                    f"mean={sum(drifts)/len(drifts)*1000:.1f}ms"
                )

        print(f"  {'-' * 54}")
        type_counts = Counter(r.get('event_type', '?') for r in records)
        parts = [f"{t}={c}" for t, c in sorted(type_counts.items())]
        print(f"  CSV: {', '.join(parts)} ({len(records)} rows)")

        print(f"{'=' * 60}\n")