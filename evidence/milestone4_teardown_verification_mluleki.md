# Teardown and Rebuild Verification — Mluleki Nkosinathi Mzelemu

Date: 2026-10-06

## What was done

1. `docker compose down -v` while the stack was already running.
   Confirmed output: both containers stopped and removed, the network
   removed, and the named volume
   `cloud-fault-service_fault_db_data` removed, meaning all persisted
   data was genuinely destroyed, not just the containers stopped.
2. `docker compose ps` immediately after: empty, nothing running.
3. `docker compose up --build -d` from that completely clean state.
4. `GET /health` returned `200` within seconds of the rebuilt
   containers starting.
5. A fresh `POST /faults` returned `201` with a correctly derived
   priority (`severity: "high"` to `priority: "P1"`), ticket
   `FR-B5DDBEE0`, correlation id `180f6dbe-541f-4cdd-964c-876caccc2f89`,
   proving the entire slice, not just the containers, works
   immediately after a full teardown and rebuild from the repository
   instructions alone.

## Result

Pass. The environment can be destroyed and recreated to a working
minimum slice without any manual repair step, satisfying the
teardown/rebuild check required by handbook §7.1.
