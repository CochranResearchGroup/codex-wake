# Coherent monitor cycle settings

The628steadyactiveprofile counted39_settings reads across10ticks (.0061s
cumulativeelapsed). A monitor cycle now reads settings once and shares that
validated dictionary with observerdeadline, publisherheartbeat andsleepdeadline.
Standalone publicpublication continues reading its own settings. Startup retains
aninitialvalidateddictionary so a failed laterread cannot leave sleepunbound.
This removes redundant filesystem/parse work and keeps each cycle coherent.

No newAPI/CLI setting or acceptancebudgetchange. Focused actualowner/publication
checks onbothPython3.11/3.12 pass5tests, including boundedquietticks, unchanged
publication, immediatechanges, completepersistedrows andenabledrouting. Command:
PYTHONPATH=src /tmp/wake216-py{311,312}/bin/python -m unittest discover -s tests
-p test_tab_monitor_publication.py . No acceptanceclaim fromthisselection.
