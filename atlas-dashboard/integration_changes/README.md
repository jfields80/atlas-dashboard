# integration_changes

No existing Atlas files were modified for Phase 3. The subsystem runs
independently, per the success criteria.

Two OPTIONAL integrations for a future sprint (do not apply until the
frozen-pipeline freeze is lifted for a Phase 4 wiring pass):

1. core/engine_versions.py — register the new engine:

       DIRECTORY_BLUEPRINT = ("directory_blueprint", "1.0.0")

   Match the existing registry pattern in that file; the constant lives in
   engines/directory_blueprint/blueprint_generator.py as
   BLUEPRINT_ENGINE_NAME / BLUEPRINT_ENGINE_VERSION.

2. services/pipeline_runner.py — add a post-committee step:

       from services import directory_blueprint_service as blueprint_service
       result = blueprint_service.generate_and_store_from_payload(conn, payload)

   where payload maps committee/capacity/classifier outputs onto the
   BlueprintRequest contract (see docs/directory_blueprint_engine.md,
   "Future extension points" #1 and #3). Record result.blueprint_id in the
   Prediction Ledger snapshot for full decision traceability.

The subsystem also computes its own input hash locally
(blueprint_generator.compute_input_hash). If core/input_hash.py exposes a
compatible canonical-JSON SHA-256, swap it in at integration time.
