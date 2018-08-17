drop function if exists until_date;
create function until_date returns datetime NO SQL DEERMINISTIC return @until_date;

-- MySQL dump 10.16  Distrib 10.3.8-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: extensions
-- ------------------------------------------------------
-- Server version	10.3.8-MariaDB-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Final view structure for view `extension_most_recent_until_date`
--

/*!50001 DROP TABLE IF EXISTS `extension_most_recent_until_date`*/;
/*!50001 DROP VIEW IF EXISTS `extension_most_recent_until_date`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `extension_most_recent_until_date` AS select `e1`.`extid` AS `extid`,`e1`.`date` AS `date`,`extensions`.`extension`.`name` AS `name`,`extensions`.`extension`.`version` AS `version`,`extensions`.`extension`.`description` AS `description`,`extensions`.`extension`.`downloads` AS `downloads`,`extensions`.`extension`.`rating` AS `rating`,`extensions`.`extension`.`ratingcount` AS `ratingcount`,`extensions`.`extension`.`fulldescription` AS `fulldescription`,`extensions`.`extension`.`developer` AS `developer`,`extensions`.`extension`.`itemcategory` AS `itemcategory`,`extensions`.`extension`.`crx_etag` AS `crx_etag`,`extensions`.`extension`.`lastupdated` AS `lastupdated`,`extensions`.`extension`.`last_modified` AS `last_modified` from (((select `extensions`.`extension`.`extid` AS `extid`,max(`extensions`.`extension`.`date`) AS `date` from `extensions`.`extension` where `extensions`.`extension`.`date` <= `until_date`() group by `extensions`.`extension`.`extid`)) `e1` join `extensions`.`extension` on(`e1`.`extid` = `extensions`.`extension`.`extid` and `e1`.`date` = `extensions`.`extension`.`date`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2018-08-09 12:31:29
