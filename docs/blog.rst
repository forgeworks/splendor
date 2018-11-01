Selecting A Version
--------------------

There are three popular ideas for how users should select a version through their requests.  Here
they are ordered in the least RESTful to the most:

**URL Selector**:
Usually by creating different path prefixes `/v1`, `/v2`, etc, we have the user adjust their URLs
in order to select what version they need.  This is really simple, popular strategy, and basically 
ensures the user must be cognizant of what version of the API they request.  Unfortunately it 
breaks a RESTful ideal that resources should only be at one location, since a resource like a *Pet* 
at `/v1/pets/42` might be exactly the same as `/v2/pets/42` we actually have two URLs for that pet.  
This can cause issues with proxies and other systems that expect URLs to be singular.

This strategy also means users must pin to a specific version.  If version 3 comes out, legacy users
won't be suddenly using it instead of version 2.

**Header Selector**:
By using a header like `X-Content-Version` we allow the user to *optionally* select what version
they want.  This makes it a little harder with some tools, like curl, because you'll have to set
a header for your request as well.  In fact generally the version is less visible than, say the
URL Selector, when you are debugging.  However, it means all the URLs are the same.

It also raises a small issue with what happens when the client doesn't set the header?  Do you give
them the latest version?  If so, when a new version comes out, you might find that legacy users,
having never had to specify their version are all getting the new version accidentally.  Another
option is to raise a 400 BadRequest suggesting the user set the header.  But there might be a lot
of confusion over this.

If you have control over both sides, the back-end API and the client, then this is a great strategy
because you can ensure the header is correctly set.

**Accept Header Version**
The most RESTful of the bunch, here we specify what version we want by adjusting the Accept header
appropriately.  This is sometimes suggested as the *correct* way to do this.

You, are of course, sending all of your requests with a full *Accept* header that contains the
content-type, format, and encoding of the response you expect back, right?  I'm not talking about
`application/json`, I'm talking about `com.example.Pet/json+gzip`.  Well just add version tag to 
that as well.

Oh, you aren't requesting it that way?  You happen to be mortal instead?  Then yes, you probably
are not going to like this selector, nor are your users.

It's also not entirely correct, as it doesn't technically say what version of the **API** you want,
it really says what version of the media type you want, which can and will be incongruent.