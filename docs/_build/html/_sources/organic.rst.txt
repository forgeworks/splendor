Organic Development
===================

The point of Organic Development is to be conscious of the natural cycles of development work.  This
allows us to maximize time and effort to focus on what matters.  Some of this might be obvious for
a certain class of programmers, but we believe it should go with saying.

The guidelines are:

1. Account for the future, but don't build for it.  Build now, only what you need now.
2. Don't optimize too early.
3. Don't abstract too early.
4. Don't test too early.
4. Stay dynamic and spontaneous early.  This fosters innovation.
5. Become static and predictable when you need to.  This fosters quality.
6. Iterate between these two phases, dynamic and static.
7. Test each phase.


**1. Account for the future, but don't build for it.  Build now, only what you need now.

Too often, as developers, we get excited about what could or will be.  We forget that we usually have
a very specific task in front of us.  We must resist the temptation to build out new features that
we fixate on, but aren't actually necessary.  Sometimes this means not adding parameters to a 
function that aren't actually used.  Sometimes this means asking our product owner if they really 
need a feature.  Either way, the point is to focus on the road ahead, and not the million paths that
the future might have for us.

That said, we should still be account for, be mindful of the future, and shouldn't paint ourselves
into corners.

**2. Stay dynamic, spontaneous, and un-optimized early so that you are not bogged down in details and can be flexible.  This fosters innovation.**

The dynamic phase is one of innovation, when we don't know exactly where we are going or how to get
there.  It is a time that requires quick iteration and change.  It must be fluid and energetic.

The main idea here is that too much code testing, documentation, and schema enforcement early bogs 
one down.  When you aren't even sure exactly what you're building, it's probably not a good idea to 
test every minor detail.  By all means, start writing tests, start writing documentation, but make 
sure it's light because you will need to update it often.

Likewise, we don't want to lock our object schemas up too tightly.  This is where things like 
non-relational databases, document stores, memory caches, etc, really shine.  Keep data ephemeral, 
which is to say, able to be completely deleted without slowing you down.

Dynamic languages like Python are particularly good in this phase, because it lets us focus on 
logic rather than schema.  And allows us to quickly iterate without compile times or getting hung
up on semi-colons.

**3. Become static, predictable, and optimized when you need to, usually when other people start using your service.  This fosters quality.**

The static phase is one of quality, when you have something and need to make sure it is tested,
documented, and communicated effectively.  It is a time that requires a lot of debugging and
structure.  It must be organized and calming.

Here we want to focus on documentation, testing, schema, etc.  As opposed to the dynamic phase,
where we wish to innovate, here we want resist innovation.  It's not new features we are after,
but rather that our already developed ones are able to execute flawlessly.  And importantly that 
all parties, our fellow developers, project managers, users, etc, are well informed of how our
system works, and that we can guarantee that it will work within our support period.

This is a great time to enforce schema.  We now know basically how our objects should work, and what
features they should have.  More traditional databases are great tools here, and critically, we
must ensure backup and migration processes are in place.

Statically-typed languages have long shined here better than languages like Python, however
with the accuracy of modern linters and some good tools to describe and enforce schema, dynamic 
languages are now arguably just as good and have the benefit of being able to support a dynamic
phase as well.

**4. Iterate between a dynamic phase to innovate new features, and a static one to ensure those features are well executed.  Test each phase.**

Within something like a sprint, ideally we go through one or many dynamic and innovative phases per 
feature.  But if we're honest, that often fails.  Often we only have time for a dynamic phase, 
but we try and cram in a static phase as well.  This is partly because we fail to estimate for the
static phase.  We imagine we can get a feature done in a certain time frame, but our static phase
is woefully underappreciated.  This builds technical debt, in essence it's time that must be spent
in a static phase.