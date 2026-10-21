## Purpose

Provides a repeatable way to confirm that the core budget-generation workflow still runs and still produces the same figures, using synthetic data only, so that later changes to budget rules can be reviewed with evidence rather than by manually reading spreadsheets.

**Data scope**: this capability reads existing data and produces no new data of its own. It affects neither Generation A nor Generation B reference tables, and it does not change any Fact/Dim join key, so the Copilot Studio package's live data is unaffected.

## Requirements

### Requirement: Verification never touches production data

Verification SHALL operate entirely on synthetic sample data. It MUST NOT read, overwrite, or otherwise modify the live project input workbook, the generated analysis workbook, or any client deliverable.

#### Scenario: Production input is left untouched
- **WHEN** verification is run while a live project input workbook exists
- **THEN** that workbook is unchanged in both content and modification time
- **AND** no file in the shared reports or deliverable folders is created, altered, or deleted

#### Scenario: Verification works with no production data present
- **WHEN** verification is run on a machine where no live project input workbook exists
- **THEN** verification still completes and reports a result

### Requirement: Verification exercises the complete core workflow

Verification SHALL run the full core workflow for the synthetic project — both the client-deliverable generator and the internal analysis generator — in the order the documented run procedure specifies.

#### Scenario: Both outputs are produced
- **WHEN** verification is run against the synthetic sample project
- **THEN** both a client-format budget workbook and an internal analysis workbook are produced
- **AND** both carry the synthetic project's name

#### Scenario: A partial run is reported as a failure
- **WHEN** one of the two generators fails to complete
- **THEN** verification fails and names which generator did not complete

### Requirement: Generated workbooks are structurally sound

Verification SHALL confirm that each generated workbook opens without repair, contains the expected sheets, contains no cell resolving to an Excel error value, and carries no file-corruption artifacts.

#### Scenario: A clean workbook passes
- **WHEN** the generated workbooks contain the expected sheets and no error values
- **THEN** verification records a structural pass

#### Scenario: A formula error fails verification
- **WHEN** any cell in a generated workbook resolves to an Excel error value after recalculation
- **THEN** verification fails
- **AND** reports the sheet and cell location of at least the first such cell

#### Scenario: A corrupted file fails verification
- **WHEN** a generated workbook contains file-corruption artifacts that would trigger an Excel repair prompt
- **THEN** verification fails and identifies the affected file

Where the source template contains a formula that is undefined until an input the pipeline controls
is populated, the pipeline SHALL populate that input or fail. It SHALL NOT emit a workbook whose
error cells depend on which rows a given run happened to write, since that makes a latent defect
appear and disappear with unrelated changes.

#### Scenario: An undefined denominator stops the run
- **WHEN** the pipeline is about to write a workbook in which a template formula would divide by an
  empty value the pipeline is responsible for supplying
- **THEN** the run fails and names the cells that would be undefined
- **AND** no deliverable is produced

#### Scenario: A latent defect does not depend on which rows were written
- **WHEN** a cost line is added to or removed from what the pipeline writes
- **THEN** whether the generated workbook contains error cells does NOT change as a result

### Requirement: Numeric results are compared against a recorded baseline

Verification SHALL compare an agreed set of headline figures from the synthetic run against previously recorded baseline values. All figures SHALL be expressed in VND with the unit stated.

#### Scenario: Unchanged figures pass
- **WHEN** every compared figure matches its recorded baseline
- **THEN** verification records a numeric pass

#### Scenario: A changed figure fails and is identified
- **WHEN** any compared figure differs from its recorded baseline
- **THEN** verification fails
- **AND** reports the figure's name, its baseline value in VND, and its current value in VND

#### Scenario: An intentional change can be re-baselined
- **WHEN** a figure has changed because of an approved change and the baseline is deliberately updated
- **THEN** the new value is recorded together with a stated reason
- **AND** subsequent runs compare against the updated baseline

### Requirement: Verification reports its own strength honestly

Verification SHALL report which checking method was actually used. When full Excel recalculation is unavailable and a weaker file-level inspection is used instead, verification MUST state this explicitly rather than presenting a reduced check as a full one.

A check that independently reconciles a figure SHALL fail when it cannot read the input it is
anchored to. It MUST NOT fall back to the artifact under test, and MUST NOT report success against
a substituted or absent value — a check that silently stops proving anything is worse than one that
fails, because it still reads as evidence.

#### Scenario: Full recalculation is available
- **WHEN** Excel recalculation can be performed
- **THEN** the result states that a full recalculation check was performed

#### Scenario: Full recalculation is unavailable
- **WHEN** Excel recalculation cannot be performed
- **THEN** the result states that only a reduced check was performed
- **AND** states that formula errors visible only on recalculation were not detectable in this run

#### Scenario: A hand-check cannot reach its input
- **WHEN** a hand-check's expected value depends on an input it cannot read from the sample fixture
- **THEN** the check reports failure
- **AND** does NOT compute its expectation from the workbook it is checking

#### Scenario: A hand-check's inputs survive a form layout change
- **WHEN** the intake form's row layout changes
- **THEN** the hand-checks read the same input values as before the change

Verification SHALL also report how much of the work was checked at all, not only whether the figures
it does check still reproduce. It SHALL report the share of a real reference budget's cost the
pipeline fills, and the share of what it writes that is computed by a method the costing
specification states. A run that reports only reproducibility SHALL NOT present itself as a
statement about coverage, method or accuracy.

#### Scenario: Coverage is reported against real reference budgets
- **WHEN** verification runs
- **THEN** it reports which cost codes a real reference budget uses that the pipeline does not fill
- **AND** reports the share of that budget's value the unfilled codes represent

#### Scenario: Method fidelity is reported against the costing specification
- **WHEN** verification runs
- **THEN** for each cost code the pipeline fills it reports whether the method used is one the
  costing specification states for that code
- **AND** reports the share of written cost that matches, partially matches, and does not match

#### Scenario: A cost code with no recorded verdict fails the run
- **WHEN** the pipeline writes a cost code that has no recorded method verdict, or stops writing one
  that has
- **THEN** verification fails and names that code
- **AND** does NOT infer a verdict, so that adding or changing a derivation cannot silently age the
  report

#### Scenario: The result summary does not overstate what was checked
- **WHEN** verification completes successfully
- **THEN** its summary states coverage and method fidelity alongside the baseline comparison
- **AND** does NOT describe the run in terms that imply the figures were checked for correctness

### Requirement: The real run procedure is documented and accurate

The change SHALL provide written documentation of how the project is actually run today, naming the real entry points in the order they must be executed, including the requirement to run both generators after any input change.

#### Scenario: Documented steps produce a working result
- **WHEN** a person follows the documented run procedure from a clean starting state
- **THEN** the workflow completes and produces both outputs

#### Scenario: The both-generators requirement is stated
- **WHEN** a reader consults the documented run procedure
- **THEN** it states that running only one generator leaves the two outputs describing different projects

### Requirement: Datasets present but unread are recorded without being connected

The change SHALL record an inventory of datasets that exist in the repository but are not read by the pipeline at runtime, each with evidence. It MUST NOT connect any of them, because doing so would move budget figures.

#### Scenario: An unread dataset is listed with evidence
- **WHEN** a dataset exists in the repository and no runtime code path reads it
- **THEN** it appears in the inventory with the evidence establishing that it is unread

#### Scenario: Recording an unread dataset changes no figure
- **WHEN** the inventory is produced
- **THEN** every baseline figure is unchanged
- **AND** no previously unread dataset has become read by the pipeline

### Requirement: Verification confirms the deliverable is built on the standard template

Verification SHALL check that the generated client deliverable was built from the current standard
budget template and carries its full sheet set. The recorded sheet-count expectation SHALL match the
standard template plus the sheets the pipeline adds itself.

This adds to the existing structural-soundness requirement; it does not change the "no formula
errors after recalculation" or "no corruption artifacts" checks, which continue to run against
whatever template is current.

#### Scenario: The deliverable carries the standard sheet set

- **WHEN** verification inspects a generated deliverable
- **THEN** every sheet name the standard template defines SHALL be present
- **AND** verification SHALL fail and name the missing sheets if any standard sheet is absent

#### Scenario: The sheet-count baseline moved with a stated reason

- **WHEN** the standard template changes and the deliverable's sheet count changes with it
- **THEN** the recorded sheet-count baseline SHALL be updated together with a stated reason
- **AND** subsequent runs compare against the updated count

#### Scenario: Figures are unchanged by the template switch

- **WHEN** verification runs after the deliverable is re-based onto a new template version
- **THEN** every compared headline figure SHALL still match its recorded baseline in VND
- **AND** a figure that changed only because of the switch SHALL be reported, not silently accepted

### Requirement: The client deliverable's ramped lines have their own recorded baseline

Verification SHALL record and compare a small set of figures read from the client deliverable
itself — the year-one total of each occupancy-scaled line and the deliverable's estimated surplus —
in addition to the analysis-workbook figures. This is because the occupancy ramp changes the
deliverable's distribution of these lines while the analysis-workbook figures (which do not use the
template) stay put.

#### Scenario: A ramped line reverting to a flat write is caught

- **WHEN** an occupancy-scaled line is written as an even one-twelfth split instead of ramped
- **THEN** verification SHALL fail and name that line

#### Scenario: The deliverable baseline is re-recordable with a stated reason

- **WHEN** the fill-up curve or a ramped line's method changes by an approved change
- **THEN** the affected deliverable baseline figures SHALL be re-recorded together with a stated
  reason
- **AND** subsequent runs compare against the updated values

#### Scenario: The deliverable and the analysis stay consistent where they should

- **WHEN** both workbooks are generated for the same project
- **THEN** the fill-up percentage each applies to a given month SHALL be the same
- **AND** any line that is deliberately shown at full occupancy in the analysis (as a stated
  ceiling) SHALL be identified as such rather than treated as a mismatch

### Requirement: Verification confirms the input-form guard

Verification SHALL confirm, on every run, that building the input form refuses to replace an
existing project input workbook without the force option, and that a forced rebuild keeps a backup.
This confirmation SHALL use a temporary folder only and MUST NOT read, create, alter or delete any
file in the live reports folder.

#### Scenario: The guard holds
- **WHEN** verification builds the form twice in a temporary folder, once without and once with the force option, over a stand-in input workbook
- **THEN** the first build is refused and leaves the stand-in unchanged
- **AND** the second build leaves a backup equal to the stand-in's earlier content and replaces the stand-in
- **AND** verification records a pass for this section

#### Scenario: A weakened guard fails verification
- **WHEN** the unforced build overwrites the stand-in workbook
- **THEN** verification fails and says the input-form guard did not hold

#### Scenario: The live reports folder is untouched
- **WHEN** this section runs while a live project input workbook exists
- **THEN** that workbook is unchanged in content and modification time

### Requirement: The management-fee revenue hand-check covers every priced product

Verification SHALL recompute the management-fee revenue of the synthetic project independently, as
the sum over every product the tool can price (apartment, officetel, office, shopping mall, retail,
shop apartment, shophouse, villas, nursery) of that product's net floor area from the input file
times its monthly fee per square metre, times 12 months, and compare the sum with the figure on the
deliverable. The result SHALL agree to within 1 VND. A product with an area of 0 in the input
contributes 0.

A product that has an area in the input but no numeric fee in the workbook's pricing table is
unpriced. It SHALL contribute 0 to the expected figure, and the check's description SHALL name each
unpriced product, so that the omission is visible rather than silent. An unpriced product on its own
SHALL NOT make the check fail.

#### Scenario: A project with an officetel passes

- **WHEN** the synthetic project has apartment, officetel and shophouse areas and all three are priced
- **THEN** the expected revenue includes the officetel (its area times its fee times 12)
- **AND** the check passes when the deliverable's figure agrees to within 1 VND

#### Scenario: A product with an area but no fee is named

- **WHEN** a product has an area in the input but no numeric fee in the pricing table
- **THEN** it contributes 0 to the expected revenue
- **AND** the check's description names it as unpriced
- **AND** the check does not fail for that reason alone

#### Scenario: An input area that disagrees with the workbook fails the check

- **WHEN** any priced product's area in the input file differs from the area in the workbook by more
  than 0.5 m²
- **THEN** the check fails and says it is not anchored to the input file

#### Scenario: A product row cannot be found in the input file

- **WHEN** the input file has no row for one of the nine products
- **THEN** the check fails and names the missing label
- **AND** does NOT compute its expectation from the workbook it is checking

### Requirement: Verification exercises the operating-project path

Verification SHALL also run the full pipeline on a second synthetic project, isolated in the same
way as the standard sample so that it cannot read or write production data. That project's intake
SHALL fill the operating-project fields:
- the stable-operation switch set to Yes;
- an actual rate with its VAT basis for at least two products, and at least one product left to
  comparables;
- actual car and motorbike parking revenue;
- collect-on-behalf amounts for at least two products.

All of its values SHALL be fictional. It SHALL NOT carry any real project's figures.

On that project, verification SHALL fail and name the figure, giving each workbook's value in VND,
when any of these holds:
- a product with an entered rate is not priced at that rate in both workbooks;
- the product left to comparables is not priced as it would be without the new fields;
- any month's resident or parking fill is not 100%;
- `RM.0A` is not zero;
- `RP1` or `RP2` is not the entered figure × 12;
- the collect-on-behalf revenue lines and their paired expense lines do not sum to the same amount
  within 1 VND.

The second project's figures SHALL be recorded as a baseline of their own. The standard synthetic
project's recorded baseline SHALL NOT move.

This reads one new fixture intake workbook under `verification/fixtures/` and writes a new baseline
file for it under `verification/baselines/`. No existing baseline figure moves.

#### Scenario: The operating-project path passes

- **WHEN** verification runs and each operating-project figure is as entered
- **THEN** the operating-project section SHALL record a pass

#### Scenario: An entered rate that one workbook ignores fails verification

- **WHEN** one workbook prices a product at the comparable-derived rate although a rate was entered
  for it
- **THEN** verification SHALL fail
- **AND** SHALL name the product with both workbooks' revenue in VND

#### Scenario: An unbalanced collect-on-behalf pair fails verification

- **WHEN** the collect-on-behalf revenue lines and their paired expense lines differ by more than 1 VND
- **THEN** verification SHALL fail
- **AND** SHALL name the pair that does not balance

#### Scenario: The standard sample is unaffected

- **WHEN** verification runs after this change
- **THEN** every figure recorded for the standard synthetic project SHALL match its recorded
  baseline without a re-record

### Requirement: Verification fails on a changed staffing line without a reason

Verification SHALL fail, naming the line, when in Existing-project mode a staffing line differs from the baseline and
carries no reason, or carries the code "Khác" without a note. It SHALL pass when every changed line has a reason.

#### Scenario: A change without a reason

- **WHEN** a generated budget has a changed staffing line with no reason
- **THEN** the verification run fails and names that line

#### Scenario: Nothing changed

- **WHEN** a generated budget has no changed staffing line
- **THEN** the check passes with nothing to report

### Requirement: Verification confirms the Staff bridge ties

Verification SHALL confirm, in Existing-project mode, that the Staff bridge total equals EMH2 plus EMH3 plus EMH4 of
the client deliverable as Excel recalculates it, and that the bridge is absent from the client deliverable. In
New-prospect mode it SHALL confirm that the bridge is not produced. Verification SHALL run the pipeline on an invented
Existing-project sample, in its own section, besides the standard New-prospect sample, whose recorded figures do not
move.

#### Scenario: The bridge disagrees with the deliverable

- **WHEN** the bridge total differs from EMH2 plus EMH3 plus EMH4
- **THEN** verification fails with both numbers

### Requirement: Verification confirms each staffing line equals its detail sheet

Verification SHALL confirm, in Existing-project mode, that EMH2, EMH3 and EMH4 are formulas into their detail sheets and
that each equals its detail sheet's total as Excel recalculates it, within 1 VND per year. Verification SHALL run this
and the other Existing-project checks on two invented samples: one with a roster, and one without a roster that carries
approved amounts, a PM override with a reason, and an approved EMH4 of zero.

#### Scenario: A typed amount on a staffing line

- **WHEN** EMH2 on the fund sheet is a number instead of a formula
- **THEN** verification fails and names the line

### Requirement: Verification exercises Existing-project utilities

`verify.py` SHALL run invented Existing-project samples that carry utility actuals and check the following:
- `EEE.C` and `EEW.C` on the client deliverable equal the Utility Bridge's budget-year figures;
- the twelve months of each line sum to its annual figure;
- the New-prospect standard sample has no Utility Bridge, and its figures equal the recorded baselines.

Unit tests SHALL cover the cases that stop a run: a missing reason, a duplicated month, a month in the budget year,
a missing tariff row, and too few months without an approved amount. The samples SHALL use invented figures only.

Data files read: the invented samples under `verification/fixtures/`, the tariff table. No recorded baseline figure
moves.

#### Scenario: The bridge does not tie

- **WHEN** the Utility Bridge's budget-year figure for `EEW.C` differs from `EEW.C`'s annual total on the deliverable by
  more than 1 VND
- **THEN** verification SHALL fail and name the line and both figures

#### Scenario: A New-prospect run shows a Utility Bridge

- **WHEN** the standard sample's analysis workbook contains a Utility Bridge sheet
- **THEN** verification SHALL fail

### Requirement: Verification exercises the run log
Verification SHALL run the run-log measurement on the synthetic project with its paths redirected, and SHALL fail when
the record is missing, when its Required-line counts do not add up to the total, when its surplus differs from revenue
minus expense, or when its figures differ from the same cells read directly through Excel. It SHALL also confirm that
a read-only run log folder produces a warning and not a failure. Verification SHALL NOT write to the live
`Budget_Agent/reports/run_log/` folder.

#### Scenario: Counts do not add up
- **WHEN** the synthetic record says 40 filled, 10 zero with a reason, 5 zero with no reason and a total of 60
- **THEN** verification fails and names the counts

#### Scenario: Production folder untouched
- **WHEN** verification finishes
- **THEN** the live run log folder holds the same files as before it started

### Requirement: Verification checks the Service Levels sheet and the service-level tables

Verification SHALL confirm, on the synthetic project, that:
- the `Service Levels` sheet's cleaning and security headcount equals the roster;
- its measures, levels and "sát ngưỡng" marks equal an independent recomputation from the threshold table;
- a value on a cut-off falls in the higher-numbered band;
- a value outside the sanity bounds is "chưa phân loại" and keeps its measure;
- the percentile's comparison set holds only form-read, classified real projects, and the count shown equals that set's size;
- the client deliverable and every other sheet are unchanged from the recorded baseline;
- the real-project table and the threshold table contain no project name or file name from the scan store;
- the real-project table holds no two rows with identical fee-paying NFA.

Verification MUST NOT read the scan store or the name-to-id map; the name check SHALL run against a list of names supplied by the build step's own output, kept outside the repository.

Data files read: `Ref_ServiceLevelThresholds.csv`, `Ref_ServiceLevelProjects.csv`.

#### Scenario: Headcount differs from the roster

- **WHEN** the sheet's cleaning headcount differs from the roster's
- **THEN** verification SHALL fail and name the service

#### Scenario: A cut-off value

- **WHEN** a synthetic project sits exactly on a threshold
- **THEN** verification SHALL confirm it is in the higher-numbered band

#### Scenario: An inferred row in the comparison set

- **WHEN** the sheet's percentile count includes a real project whose source is "chi phí"
- **THEN** verification SHALL fail and name the service

#### Scenario: A name in the table

- **WHEN** a store project name appears in either data table
- **THEN** verification SHALL fail

#### Scenario: Duplicate NFA in the table

- **WHEN** two rows of the real-project table carry the same fee-paying NFA
- **THEN** verification SHALL fail and list the two ids

### Requirement: Verification exercises every path the PM decisions add

Verification SHALL run invented samples that reach each new path:
- a project with coordinates, so the distance ranking runs;
- a filled Savills fee, once fixed and once as a %;
- two Accountants and two Property Managers, so the `A1` overflow rows are written;
- a qualifying 24/7 position and a night position, so `A1.1` is filled;
- a non-default budget start month, a water customer group and an entered ESI2 premium.

It SHALL tie each staffing line to its detail sheet on the standard sample as well as on the Existing samples. It SHALL
confirm the helper-sheet ties and the contingency formulas. It SHALL run the deliverable name scan on every sample.

#### Scenario: A double-counted allowance

- **WHEN** a change makes `EMH2` include the `A1.1` allowance while `EMH3` also carries it
- **THEN** verification SHALL fail on the standard sample

#### Scenario: Distance path reached

- **WHEN** verification runs
- **THEN** at least one sample SHALL reach the distance ranking, and its result SHALL be checked

### Requirement: The baselines are re-recorded once for this change, with each movement measured

Each decision SHALL be measured on its own, before and after, on the standard sample and on a regression clone kept
outside the repository, and the movement in VND SHALL be recorded in the change. The recorded baselines (analysis,
deliverable, operating) SHALL be re-recorded once, after every decision is built, with the reason written beside the
new figures.

#### Scenario: Re-record

- **WHEN** every decision in this change is built and measured
- **THEN** the baselines SHALL be re-recorded in one step, with the reason stated
- **AND** verification SHALL pass against the new baselines

### Requirement: Verification confirms the real-budget ranges

`verify.py` SHALL check, on the standard sample and on an Existing-project sample:
- every code priced from the range has the same figure on the `Real-Budget Ranges` sheet and on
  `2. Budget-Management Fund`;
- each range used holds at least 10 projects;
- the project's own entry is left out, on a fixture whose project is in the data file;
- the data file carries none of a list of names supplied as a fixture.

A broken deliverable, with one priced line typed 1,000 VND off, SHALL fail the tie check. The fixtures SHALL contain
no real project name or figure.

Data files read: the generated workbooks, `Ref_RealBudgetValues.csv`, and the verification fixtures. Recorded
baseline figures move once, with the user's approval (design D7).

#### Scenario: A priced line typed off

- **WHEN** the deliverable's `ESS12` differs from the sheet by 1,000 VND
- **THEN** the check SHALL fail and name `ESS12` and both figures

#### Scenario: The project itself is in the data file

- **WHEN** the fixture project matches an entry in the data file
- **THEN** the check SHALL confirm that entry is not among the values used
