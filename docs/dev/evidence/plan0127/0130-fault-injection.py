import os
if os.environ.get("PLAN130_FAULT_PHASE"):
    import codex_wake.native_delivery as delivery
    original = delivery.replace_record
    def checkpoint(root, found, record):
        if record.get("id") == os.environ.get("PLAN130_FAULT_WAKE"):
            state = record.get("native_delivery", {}).get("state")
            phase = os.environ["PLAN130_FAULT_PHASE"]
            if phase == "before-submission" and state == "uncertain":
                os._exit(90)
            if phase == "after-intent" and state == "uncertain":
                original(root, found, record)
                os._exit(92)
            if phase == "after-acceptance" and state == "accepted":
                os._exit(91)
        return original(root, found, record)
    delivery.replace_record = checkpoint
