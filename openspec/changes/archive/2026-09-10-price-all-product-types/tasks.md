## 1. Record the starting point

- [x] 1.1 Capture the figures this change should move and the ones it must not — the deliverable's total management-fee revenue as the mover, and `mgmt_fee_revenue_annual`, `total_profit_value`, `margin` and `markup` from the analysis as controls that must hold — verify by reading each from `verification/baselines/baseline.json` and from a generated deliverable, and recording the values before any code is touched
- [x] 1.2 Confirm verification passes before the change — verify by running `python verification/verify.py` and confirming it exits zero

## 2. Price every product in the deliverable

- [x] 2.1 Replace the single revenue row with a per-product mapping from product name to template row, covering the nine product rows in the Management Fund sheet — verify by confirming each mapped row number carries the product label the mapping claims, read back from the generated file
- [x] 2.2 Write each product's revenue from its own NFA and its own derived rate — verify by confirming the deliverable's per-product figures match the analysis workbook's, product by product
- [x] 2.3 Leave a product with no area blank rather than zero — verify by confirming the sample's unused product rows are empty in the generated file
- [x] 2.4 Confirm the deliverable's total management-fee revenue now equals the analysis workbook's — verify by comparing the two totals from a single run and confirming the 1,930,800,000 VND class of gap is closed
- [x] 2.5 State the rate basis in each product row's remarks, naming the comparables for a real rate and stating the substitution for a fallback — verify by reading the generated remarks and confirming a fallback row cannot be mistaken for a real product rate

## 3. Extend the intake form

- [x] 3.1 Add Office, Retail, Shop Apartment and Villas to the Product Mix block — verify by generating a fresh input form into a scratch location and confirming the four rows are present with the same columns as the existing products
- [x] 3.2 Confirm the form offers exactly the products the pipeline can price — verify by checking no field exists for a product with no revenue row, and no priced product lacks a field
- [x] 3.3 Confirm the reader is not misled about generating the form over live input — verify by confirming the documented warning about overwriting an existing input workbook still stands and still applies to the extended form

## 4. Prove the new products actually work

- [x] 4.1 Exercise the four new products with a temporary input variant carrying area for each — verify by confirming each one is priced, written to its own template row, and appears in both workbooks
- [x] 4.2 Confirm a product with no real per-product rate falls back to the Apartment rate — verify by checking a fallback product's rate equals the derived Apartment rate and that its remark says so
- [x] 4.3 Confirm a product with a real per-product rate does not fall back — verify by checking its rate differs from the Apartment rate where the comparable data provides one
- [x] 4.4 Confirm the temporary variant left nothing behind — verify by checking the synthetic fixture is byte-identical to before and no scratch file remains in the repository

## 5. Verify the movement is the predicted one

- [x] 5.1 Run verification and confirm which figures moved — verify by running `python verification/verify.py` and confirming the analysis-side figures named in 1.1 are unchanged, since this change brings the deliverable up to the analysis rather than altering the analysis
- [x] 5.2 Confirm the deliverable's revenue rose by the predicted amount — verify by checking the total rose to the analysis figure, approximately 727,830,000 VND on the synthetic sample
- [x] 5.3 Confirm the structural checks still pass — verify by confirming sheets, corruption artifacts and Excel formula errors are all clean, and that the checking method reported is full recalculation
- [x] 5.4 Confirm production data was untouched throughout — verify by comparing the four production fingerprints against their recorded values

## 6. Re-record the baseline if it moved

- [x] 6.1 Review every named difference and confirm each was intended — verify by producing a short written account before re-recording anything, and by explaining any analysis-side movement rather than accepting it
- [x] 6.2 Re-record the baseline with a reason identifying this change, if any tracked figure moved — verify by running `python verification/baseline.py --record --reason "..."` and confirming the stored reason names this change
- [x] 6.3 Confirm verification passes on the following run — verify by running `python verification/verify.py` and confirming it exits zero

## 7. Documentation

- [x] 7.1 Record in `docs/05-decisions.md` that D2 is implemented, with the measured effect and the number of products that fell back to the Apartment rate — verify by confirming the decision's status is no longer "decided, not implemented"
- [x] 7.2 Update the run procedure to describe the extended Product Mix block — verify by confirming `RUNNING.md` names the nine products a project can be quoted for
- [x] 7.3 Update `docs/project-status.md` with the new state and the next decided change — verify by confirming it names the correct active change and next action
