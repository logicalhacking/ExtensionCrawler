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
-- Final view structure for view `extension_most_recent`
--

/*!50001 DROP TABLE IF EXISTS `extension_most_recent`*/;
/*!50001 DROP VIEW IF EXISTS `extension_most_recent`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`writer`@`%` SQL SECURITY DEFINER */
/*!50001 VIEW `extension_most_recent` AS select `e3`.`extid` AS `extid`,`e3`.`date` AS `date`,`e3`.`name` AS `name`,`e3`.`version` AS `version`,`e3`.`description` AS `description`,`e3`.`downloads` AS `downloads`,`e3`.`rating` AS `rating`,`e3`.`ratingcount` AS `ratingcount`,`e3`.`fulldescription` AS `fulldescription`,`e3`.`offeredby` AS `offeredby`,`e3`.`developer` AS `developer`,`e3`.`itemcategory` AS `itemcategory`,`e3`.`crx_etag` AS `crx_etag`,`e3`.`lastupdated` AS `lastupdated` from (((select `e1`.`extid` AS `extid`,max(`e1`.`date`) AS `date` from `extensions`.`extension` `e1` group by `e1`.`extid`)) `e2` join `extensions`.`extension` `e3` on(`e2`.`extid` = `e3`.`extid` and `e2`.`date` = `e3`.`date`)) */;
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
