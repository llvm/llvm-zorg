import config
from zorg.buildbot.util.phasedbuilderutils import getPhaseBuilderFactory, PublishGoodBuild

# Load the phase information.
import phase_config
reload(phase_config)
from phase_config import phases

def get_builders():
    phaseRunners = ['macpro1']
    # This builder should announce good builds and prepare potential release
    # candidates.
    yield { 'name' : 'Validated Build', 'factory' : PublishGoodBuild(),
            'slavenames' : phaseRunners, 'category' : 'status'}
    # These builds coordinate and gate each phase as part of the staged design.
    for phase in phases:
        if phase is phases[-1]:
            next_phase = 'GoodBuild'
        else:
            next_phase = 'phase%d' % (phase['number'] + 1)
        # Split the phase builders into separate stages.
        split_stages = config.schedulers.get_phase_stages(phase)
        yield { 'name' : 'phase%d - %s' % (phase['number'], phase['name']),
                'factory' : getPhaseBuilderFactory(config, phase, next_phase, 
                                                   split_stages),
                'slavenames' : phaseRunners, 'category' : 'status'}
    # Add the builders for each phase.
    import builderconstruction
    for phase in phases:
        for info in phase['builders']:
            builder = builderconstruction.construct(info['name'])
            builder['category'] = info['category']
            builder['slavenames'] = list(info['slaves'])
            if builder.has_key('properties'):
                props = builder['properties']
                props ['category'] = info['category']
                builder['properties'] = props
            else:
                builder['properties'] = {'category': info['category']}
            yield builder
