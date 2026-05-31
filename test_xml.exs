Mix.install([
  {:req, "~> 0.5.0"},
  {:sweet_xml, "~> 0.7.4"}
])

import SweetXml

response = Req.get!("https://feeds.megaphone.fm/nagara")
xml_body = response.body

# Get the first item
first_item = xml_body |> xpath(~x"//item[1]")
title = first_item |> xpath(~x"./title/text()"s)
pub_date = first_item |> xpath(~x"./pubDate/text()"s)

IO.puts("TITLE: #{title}")
IO.puts("DATE: #{pub_date}")
