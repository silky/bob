/**
 * @author Andre Anjos <andre.anjos@idiap.ch>
 * @date Mon 26 Nov 17:34:12 2012
 *
 * @brief A set of methods to grab information from ffmpeg.
 *
 * Copyright (C) 2011-2012 Idiap Research Institute, Martigny, Switzerland
 * 
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3 of the License.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include<boost/token_iterator.hpp>

#include "bob/io/VideoUtilities.h"
#include "bob/core/logging.h"

namespace ffmpeg = bob::io::detail::ffmpeg;

void ffmpeg::codecs_installed (std::map<std::string, const AVCodec*>& installed) {
  for (AVCodec* it = av_codec_next(0); it != 0; it = av_codec_next(it) ) {
# if LIBAVCODEC_VERSION_MAJOR >= 53
    if (it->type == AVMEDIA_TYPE_VIDEO) {
# else
    if (it->type == CODEC_TYPE_VIDEO) {
# endif
      auto exists = installed.find(std::string(it->name));
      if (exists != installed.end()) {
        bob::core::warn << "Not overriding video codec \"" << it->long_name 
          << "\" (" << it->name << ")" << std::endl;
      }
      else installed[it->name] = it;
    }
  }
}

void ffmpeg::iformats_installed (std::map<std::string, AVInputFormat*>& installed) {
  for (AVInputFormat* it = av_iformat_next(0); it != 0; it = av_iformat_next(it) ) {

    boost::char_separator<char> sep(",");
    std::string name(it->name);
    boost::tokenizer< boost::char_separator<char> > tok(name, sep);
    for (auto k = tok.begin(); k != tok.end(); ++k) {
      auto exists = installed.find(*k);
      if (exists != installed.end()) {
        bob::core::warn << "Not overriding input video format \"" 
          << it->long_name << "\" (" << *k 
          << ") which is already assigned to \"" << exists->second->long_name 
          << "\"" << std::endl;
      }
      else installed[*k] = it;
    }
    if (!it->extensions) continue;
    std::string extensions(it->extensions);
    boost::tokenizer< boost::char_separator<char> > tok2(extensions, sep);
    for (auto k = tok2.begin(); k != tok2.end(); ++k) {
      auto exists = installed.find(*k);
      if (exists != installed.end()) {
        bob::core::warn << "Not overriding input video format \"" 
          << it->long_name << "\" (" << *k
          << ") which is already assigned to \"" << exists->second->long_name 
          << "\"" << std::endl;
      }
      else installed[*k] = it;
    }
  }
}

void ffmpeg::oformats_installed (std::map<std::string, AVOutputFormat*>& installed) {
  for (AVOutputFormat* it = av_oformat_next(0); it != 0; it = av_oformat_next(it) ) {
    if (!it->video_codec) continue;
    boost::char_separator<char> sep(",");
    std::string name(it->name);
    boost::tokenizer< boost::char_separator<char> > tok(name, sep);
    for (auto k = tok.begin(); k != tok.end(); ++k) {
      auto exists = installed.find(*k);
      if (exists != installed.end()) {
        bob::core::warn << "Not overriding output video format \""
          << it->long_name << "\" (" << *k 
          << ") which is already assigned to \"" << exists->second->long_name 
          << "\"" << std::endl;
      }
      else installed[*k] = it;
    }
    if (!it->extensions) continue;
    std::string extensions(it->extensions);
    boost::tokenizer< boost::char_separator<char> > tok2(extensions, sep);
    for (auto k = tok2.begin(); k != tok2.end(); ++k) {
      auto exists = installed.find(*k);
      if (exists != installed.end()) {
        bob::core::warn << "Not overriding output video format \""
          << it->long_name << "\" (" << *k 
          << ") which is already assigned to \"" << exists->second->long_name 
          << "\"" << std::endl;
      }
      else installed[*k] = it;
    }
  }
}